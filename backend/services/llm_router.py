"""
LLM Router for optimal model selection per task.
Routes different tasks to the most appropriate LLM based on performance benchmarks.
"""
import os
from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from loguru import logger
import openai
import anthropic
from datetime import datetime


class TaskType(Enum):
    """Different types of tasks requiring LLM processing."""
    TRADE_EXPLANATION = "trade_explanation"
    SENTIMENT_CLASSIFICATION = "sentiment_classification"
    MARKET_REGIME_DETECTION = "market_regime_detection"
    CONFIDENCE_CALIBRATION = "confidence_calibration"
    DAILY_SUMMARY = "daily_summary"
    BACKTEST_REVIEW = "backtest_review"
    ERROR_DEBUGGING = "error_debugging"
    STRATEGY_GENERATION = "strategy_generation"
    LIGHTWEIGHT_TASKS = "lightweight_tasks"


class LLMProvider(Enum):
    """Available LLM providers."""
    OPENAI_GPT4O = "gpt-4o"
    OPENAI_GPT35_TURBO = "gpt-3.5-turbo"
    CLAUDE_OPUS_4 = "claude-opus-4-20250514"
    CLAUDE_SONNET_4 = "claude-sonnet-4-20250514"


@dataclass
class LLMConfig:
    """Configuration for LLM usage."""
    provider: LLMProvider
    max_tokens: int
    temperature: float
    cost_per_1k_tokens: float
    context_window: int


class LLMRouter:
    """Routes tasks to optimal LLMs based on task type and performance requirements."""
    
    # Optimal LLM mapping based on benchmarks
    TASK_LLM_MAPPING = {
        TaskType.TRADE_EXPLANATION: LLMProvider.OPENAI_GPT4O,
        TaskType.SENTIMENT_CLASSIFICATION: LLMProvider.CLAUDE_SONNET_4,
        TaskType.MARKET_REGIME_DETECTION: LLMProvider.CLAUDE_OPUS_4,
        TaskType.CONFIDENCE_CALIBRATION: LLMProvider.CLAUDE_OPUS_4,
        TaskType.DAILY_SUMMARY: LLMProvider.OPENAI_GPT4O,
        TaskType.BACKTEST_REVIEW: LLMProvider.CLAUDE_OPUS_4,
        TaskType.ERROR_DEBUGGING: LLMProvider.CLAUDE_OPUS_4,
        TaskType.STRATEGY_GENERATION: LLMProvider.CLAUDE_SONNET_4,
        TaskType.LIGHTWEIGHT_TASKS: LLMProvider.OPENAI_GPT35_TURBO,
    }
    
    # LLM configurations
    LLM_CONFIGS = {
        LLMProvider.OPENAI_GPT4O: LLMConfig(
            provider=LLMProvider.OPENAI_GPT4O,
            max_tokens=4000,
            temperature=0.7,
            cost_per_1k_tokens=0.03,
            context_window=128000
        ),
        LLMProvider.OPENAI_GPT35_TURBO: LLMConfig(
            provider=LLMProvider.OPENAI_GPT35_TURBO,
            max_tokens=2000,
            temperature=0.7,
            cost_per_1k_tokens=0.002,
            context_window=16000
        ),
        LLMProvider.CLAUDE_OPUS_4: LLMConfig(
            provider=LLMProvider.CLAUDE_OPUS_4,
            max_tokens=4000,
            temperature=0.7,
            cost_per_1k_tokens=0.075,
            context_window=200000
        ),
        LLMProvider.CLAUDE_SONNET_4: LLMConfig(
            provider=LLMProvider.CLAUDE_SONNET_4,
            max_tokens=4000,
            temperature=0.7,
            cost_per_1k_tokens=0.03,
            context_window=200000
        ),
    }
    
    def __init__(self, config=None):
        """Initialize LLM router with API clients."""
        self.config = config
        
        # Initialize OpenAI client
        self.openai_client = openai.OpenAI(
            api_key=os.getenv('OPENAI_API_KEY')
        )
        
        # Initialize Anthropic client
        try:
            self.anthropic_client = anthropic.Anthropic(
                api_key=os.getenv('ANTHROPIC_API_KEY')
            )
        except Exception as e:
            logger.warning(f"Failed to initialize Anthropic client in LLMRouter: {e}")
            self.anthropic_client = None
        
        # Usage tracking
        self.usage_stats = {}
        
        logger.info("LLM Router initialized with multi-model support")
    
    def route_task(self, task_type: TaskType, prompt: str, 
                   context: Optional[Dict[str, Any]] = None,
                   override_llm: Optional[LLMProvider] = None) -> Dict[str, Any]:
        """
        Route a task to the optimal LLM.
        
        Args:
            task_type: Type of task to perform
            prompt: The prompt to send to the LLM
            context: Additional context for the task
            override_llm: Override the default LLM selection
            
        Returns:
            Dict containing response and metadata
        """
        try:
            # Select LLM
            selected_llm = override_llm or self.TASK_LLM_MAPPING[task_type]
            config = self.LLM_CONFIGS[selected_llm]
            
            # Prepare enhanced prompt with task-specific instructions
            enhanced_prompt = self._enhance_prompt(task_type, prompt, context)
            
            # Route to appropriate LLM
            if selected_llm in [LLMProvider.OPENAI_GPT4O, LLMProvider.OPENAI_GPT35_TURBO]:
                response = self._call_openai(selected_llm, enhanced_prompt, config)
            else:
                response = self._call_anthropic(selected_llm, enhanced_prompt, config)
            
            # Track usage
            self._track_usage(selected_llm, task_type)
            
            return {
                'response': response,
                'llm_used': selected_llm.value,
                'task_type': task_type.value,
                'timestamp': datetime.now(),
                'cost_estimate': self._estimate_cost(enhanced_prompt, response, config)
            }
            
        except Exception as e:
            logger.error(f"Error routing task {task_type.value}: {e}")
            return {
                'response': f"Error: {str(e)}",
                'llm_used': 'error',
                'task_type': task_type.value,
                'timestamp': datetime.now(),
                'cost_estimate': 0
            }
    
    def _enhance_prompt(self, task_type: TaskType, prompt: str, 
                       context: Optional[Dict[str, Any]] = None) -> str:
        """Enhance prompt with task-specific instructions."""
        
        task_instructions = {
            TaskType.TRADE_EXPLANATION: """
You are an expert trading analyst. Explain this trade decision with:
1. Clear reasoning combining technical and fundamental factors
2. Specific data points that influenced the decision
3. Risk assessment and expected outcomes
4. Market context and timing rationale
Be precise, factual, and avoid speculation.
""",
            TaskType.SENTIMENT_CLASSIFICATION: """
You are a financial sentiment analysis expert. Classify the sentiment with:
1. Overall sentiment: BULLISH, BEARISH, or NEUTRAL
2. Confidence level (0-100%)
3. Key phrases that drove the classification
4. Potential sarcasm or uncertainty indicators
5. Context-aware interpretation (market conditions, timing, source)
""",
            TaskType.MARKET_REGIME_DETECTION: """
You are a market regime analysis expert. Analyze the market state considering:
1. Current volatility patterns and regime characteristics
2. Historical context and regime transitions
3. Multiple timeframe analysis
4. Correlation patterns across asset classes
5. Confidence in regime classification with uncertainty bounds
""",
            TaskType.CONFIDENCE_CALIBRATION: """
You are a risk assessment expert. Calibrate confidence levels by:
1. Identifying sources of uncertainty
2. Quantifying confidence intervals
3. Considering model limitations and data quality
4. Providing probabilistic reasoning
5. Suggesting risk mitigation strategies
""",
            TaskType.DAILY_SUMMARY: """
You are a trading summary specialist. Create a comprehensive daily summary with:
1. Key market movements and their drivers
2. Notable trades and their outcomes
3. Performance metrics and statistics
4. Market regime changes and implications
5. Clear, readable narrative combining data and insights
""",
            TaskType.BACKTEST_REVIEW: """
You are a quantitative strategy analyst. Review this backtest with:
1. Performance breakdown by time periods and market conditions
2. Risk-adjusted metrics analysis
3. Drawdown analysis and recovery patterns
4. Strategy weakness identification
5. Specific recommendations for improvement
""",
            TaskType.ERROR_DEBUGGING: """
You are a systematic debugging expert. Analyze this error with:
1. Root cause analysis with logical reasoning
2. Step-by-step troubleshooting approach
3. Potential solutions ranked by likelihood
4. Prevention strategies for similar issues
5. System-wide impact assessment
""",
            TaskType.STRATEGY_GENERATION: """
You are a creative trading strategy designer. Generate strategies that are:
1. Novel yet grounded in market principles
2. Specific with clear entry/exit rules
3. Risk-managed with defined parameters
4. Backtestable with measurable criteria
5. Adaptive to different market regimes
""",
            TaskType.LIGHTWEIGHT_TASKS: """
You are an efficient task processor. Complete this task:
1. Quickly and accurately
2. Following exact specifications
3. Minimal verbose explanation
4. Focus on the requested output format
"""
        }
        
        instruction = task_instructions.get(task_type, "")
        
        enhanced = f"{instruction}\n\n"
        if context:
            enhanced += f"Context: {context}\n\n"
        enhanced += f"Task: {prompt}"
        
        return enhanced
    
    def _call_openai(self, llm: LLMProvider, prompt: str, config: LLMConfig) -> str:
        """Call OpenAI API."""
        try:
            response = self.openai_client.chat.completions.create(
                model=llm.value,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=config.max_tokens,
                temperature=config.temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    def _call_anthropic(self, llm: LLMProvider, prompt: str, config: LLMConfig) -> str:
        """Call Anthropic API."""
        try:
            response = self.anthropic_client.messages.create(
                model=llm.value,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise
    
    def _track_usage(self, llm: LLMProvider, task_type: TaskType):
        """Track LLM usage statistics."""
        key = f"{llm.value}_{task_type.value}"
        if key not in self.usage_stats:
            self.usage_stats[key] = {'count': 0, 'last_used': None}
        
        self.usage_stats[key]['count'] += 1
        self.usage_stats[key]['last_used'] = datetime.now()
    
    def _estimate_cost(self, prompt: str, response: str, config: LLMConfig) -> float:
        """Estimate API call cost."""
        # Rough token estimation (4 chars per token average)
        total_chars = len(prompt) + len(response)
        estimated_tokens = total_chars / 4
        return (estimated_tokens / 1000) * config.cost_per_1k_tokens
    
    def get_usage_report(self) -> Dict[str, Any]:
        """Get usage statistics report."""
        total_calls = sum(stat['count'] for stat in self.usage_stats.values())
        
        return {
            'total_calls': total_calls,
            'usage_by_model': self.usage_stats,
            'generated_at': datetime.now()
        }


# Convenience functions for easy integration
def explain_trade(trade_data: Dict[str, Any], router: LLMRouter) -> str:
    """Explain a trade decision using optimal LLM."""
    prompt = f"""
    Explain this trade decision:
    Symbol: {trade_data.get('symbol')}
    Action: {trade_data.get('action')}
    Price: ${trade_data.get('price')}
    Quantity: {trade_data.get('quantity')}
    Signals: {trade_data.get('signals')}
    Market Conditions: {trade_data.get('market_context')}
    """
    
    result = router.route_task(TaskType.TRADE_EXPLANATION, prompt, trade_data)
    return result['response']


def classify_sentiment(text: str, router: LLMRouter) -> Dict[str, Any]:
    """Classify sentiment using optimal LLM."""
    prompt = f"Classify the financial sentiment of this text: {text}"
    
    result = router.route_task(TaskType.SENTIMENT_CLASSIFICATION, prompt)
    return result


def detect_market_regime(market_data: Dict[str, Any], router: LLMRouter) -> Dict[str, Any]:
    """Detect market regime using optimal LLM."""
    prompt = f"""
    Analyze the current market regime based on this data:
    {market_data}
    """
    
    result = router.route_task(TaskType.MARKET_REGIME_DETECTION, prompt, market_data)
    return result
