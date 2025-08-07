"""
Polygon Flat Files Manager
Bulk historical data download and management using S3
"""

import boto3
import asyncio
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any
from loguru import logger
import gzip
import csv
from io import StringIO

class PolygonFlatFilesManager:
    """Manager for Polygon.io Flat Files via S3."""
    
    def __init__(self):
        # S3 Configuration from your credentials
        self.s3_client = boto3.client(
            's3',
            endpoint_url='https://files.polygon.io',
            aws_access_key_id='350b2bfb-1e34-4321-bf7c-2b00ea05282f',
            aws_secret_access_key='yFR7VHO3qzDtTH9IhI4ZJvU3ukXDhOT_',
        )
        self.bucket_name = 'flatfiles'
        
        # Local storage paths
        self.data_dir = Path('data/polygon_flatfiles')
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("Polygon Flat Files Manager initialized")
        logger.info(f"Data directory: {self.data_dir.absolute()}")
    
    async def list_available_datasets(self, asset_class: str = 'stocks') -> List[Dict[str, str]]:
        """List available flat file datasets."""
        try:
            # Common flat file paths
            prefixes = [
                f'us_{asset_class}_sip/trades_v1/',
                f'us_{asset_class}_sip/quotes_v1/', 
                f'us_{asset_class}_sip/minute_aggs_v1/',
                f'us_{asset_class}_sip/day_aggs_v1/',
            ]
            
            datasets = []
            for prefix in prefixes:
                try:
                    response = self.s3_client.list_objects_v2(
                        Bucket=self.bucket_name,
                        Prefix=prefix,
                        MaxKeys=10  # Just get a sample
                    )
                    
                    if 'Contents' in response:
                        for obj in response['Contents']:
                            datasets.append({
                                'key': obj['Key'],
                                'size': obj['Size'],
                                'modified': obj['LastModified'],
                                'dataset_type': self._extract_dataset_type(obj['Key'])
                            })
                            
                except Exception as e:
                    logger.debug(f"No data found for prefix {prefix}: {e}")
            
            logger.info(f"Found {len(datasets)} available flat file datasets")
            return datasets
            
        except Exception as e:
            logger.error(f"Error listing datasets: {e}")
            return []
    
    def _extract_dataset_type(self, s3_key: str) -> str:
        """Extract dataset type from S3 key."""
        if 'trades' in s3_key:
            return 'trades'
        elif 'quotes' in s3_key:
            return 'quotes'
        elif 'minute_aggs' in s3_key:
            return 'minute_aggregates'
        elif 'day_aggs' in s3_key:
            return 'daily_aggregates'
        else:
            return 'unknown'
    
    async def download_historical_data(self, 
                                     dataset_type: str = 'day_aggs_v1',
                                     date: str = None,
                                     symbols: List[str] = None) -> Optional[pd.DataFrame]:
        """Download specific historical data."""
        try:
            if not date:
                # Default to previous trading day
                date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            
            # Construct S3 key
            s3_key = f'us_stocks_sip/{dataset_type}/{date}.csv.gz'
            
            logger.info(f"Downloading flat file: {s3_key}")
            
            # Download file
            local_file = self.data_dir / f'{dataset_type}_{date}.csv.gz'
            
            try:
                self.s3_client.download_file(
                    self.bucket_name, 
                    s3_key, 
                    str(local_file)
                )
                logger.info(f"Downloaded: {local_file}")
                
                # Read and process the data
                df = pd.read_csv(local_file, compression='gzip')
                
                # Filter by symbols if provided
                if symbols:
                    df = df[df['ticker'].isin(symbols)]
                    logger.info(f"Filtered data to {len(df)} rows for symbols: {symbols}")
                
                return df
                
            except self.s3_client.exceptions.NoSuchKey:
                logger.warning(f"File not found: {s3_key}")
                return None
                
        except Exception as e:
            logger.error(f"Error downloading historical data: {e}")
            return None
    
    async def get_bulk_historical_data(self, 
                                     symbols: List[str],
                                     start_date: str,
                                     end_date: str,
                                     data_type: str = 'day_aggs_v1') -> pd.DataFrame:
        """Get bulk historical data for multiple days."""
        all_data = []
        
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        current_date = start
        while current_date <= end:
            # Skip weekends
            if current_date.weekday() < 5:
                date_str = current_date.strftime('%Y-%m-%d')
                
                data = await self.download_historical_data(
                    dataset_type=data_type,
                    date=date_str,
                    symbols=symbols
                )
                
                if data is not None and not data.empty:
                    all_data.append(data)
                    logger.info(f"Added {len(data)} rows for {date_str}")
                
                # Rate limiting - be respectful to S3
                await asyncio.sleep(0.1)
            
            current_date += timedelta(days=1)
        
        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            logger.info(f"Combined {len(combined_df)} total rows of historical data")
            return combined_df
        
        return pd.DataFrame()
    
    def get_local_cache_status(self) -> Dict[str, Any]:
        """Get status of locally cached flat files."""
        cache_files = list(self.data_dir.glob('*.csv.gz'))
        
        status = {
            'total_files': len(cache_files),
            'total_size_mb': sum(f.stat().st_size for f in cache_files) / (1024 * 1024),
            'files': []
        }
        
        for file in cache_files:
            status['files'].append({
                'name': file.name,
                'size_mb': file.stat().st_size / (1024 * 1024),
                'modified': datetime.fromtimestamp(file.stat().st_mtime),
            })
        
        return status
    
    async def preload_watchlist_data(self, symbols: List[str], days: int = 30):
        """Preload historical data for watchlist symbols."""
        logger.info(f"Preloading {days} days of data for {len(symbols)} symbols")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Download daily aggregates (most useful for analysis)
        daily_data = await self.get_bulk_historical_data(
            symbols=symbols,
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            data_type='day_aggs_v1'
        )
        
        if not daily_data.empty:
            # Save to local cache for fast access
            cache_file = self.data_dir / f'watchlist_daily_{days}d.csv'
            daily_data.to_csv(cache_file, index=False)
            logger.info(f"Cached watchlist data: {cache_file}")
            
            return daily_data
        
        return pd.DataFrame()

# Global instance
flat_files_manager = PolygonFlatFilesManager()

# Export for easy importing
__all__ = ['flat_files_manager', 'PolygonFlatFilesManager']
