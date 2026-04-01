import os
import pandas as pd

def load_trading_data(data_folder: str, round: int, days: list[int]) -> dict[str, pd.DataFrame]:
    """
    Load trading data from CSV files into pandas DataFrames.

    Args:
        data_folder (str): Path to the folder containing the CSV files
        round (int): Round to load data for
        days (list): List of days for which data is available

    Returns:
        Dict[str, pd.DataFrame]: Dictionary containing the following DataFrames:
            - 'prices': Price data for all days
            - 'trades': Trade data for all days
    """
    data = {
        'prices': [],
        'trades': [],
        'observations': []
    }

    # Load data for each day
    for day in days:
        # Load price data
        price_file = os.path.join(data_folder, f'prices_round_{round}_day_{day}.csv')
        if os.path.exists(price_file):
            price_df = pd.read_csv(price_file, sep=';')
            # Add day column
            price_df['day'] = day
            # Convert timestamp if it exists
            if 'timestamp' in price_df.columns:
                price_df = price_df.sort_values('timestamp')
            data['prices'].append(price_df)

        # Load trade data
        trade_file = os.path.join(data_folder, f'trades_round_{round}_day_{day}.csv')
        if os.path.exists(trade_file):
            trade_df = pd.read_csv(trade_file, sep=';')
            trade_df['day'] = day
            if 'timestamp' in trade_df.columns:
                trade_df = trade_df.sort_values('timestamp')
            data['trades'].append(trade_df)

        # Load observation data
        observation_file = os.path.join(data_folder, f'observations_round_{round}_day_{day}.csv')
        if os.path.exists(observation_file):
            observation_df = pd.read_csv(observation_file, sep=',')
            observation_df['day'] = day
            if 'timestamp' in observation_df.columns:
                observation_df = observation_df.sort_values('timestamp')
            data['observations'].append(observation_df)

    # Concatenate all days' data
    result = {}
    for key, dfs in data.items():
        if dfs:  # Only add if we found any data
            result[key] = pd.concat(dfs, ignore_index=True)

    return result

def get_product_data(df: pd.DataFrame, product: str) -> pd.DataFrame:
    """
    Filter DataFrame for a specific product.

    Args:
        df (pd.DataFrame): DataFrame containing trading data
        product (str): Product name to filter for

    Returns:
        pd.DataFrame: Filtered DataFrame containing only data for the specified product
    """
    return df[df['product'] == product]

def get_day_data(df: pd.DataFrame, day: int) -> pd.DataFrame:
    """
    Filter DataFrame for a specific day.

    Args:
        df (pd.DataFrame): DataFrame containing trading data
        day (int): Day number to filter for

    Returns:
        pd.DataFrame: Filtered DataFrame containing only data for the specified day
    """
    return df[df['day'] == day]

def get_product_day_data(df: pd.DataFrame, product: str, day: int) -> pd.DataFrame:
    """
    Filter DataFrame for a specific product and day.

    Args:
        df (pd.DataFrame): DataFrame containing trading data
        product (str): Product name to filter for
        day (int): Day number to filter for

    Returns:
        pd.DataFrame: Filtered DataFrame containing only data for the specified product and day
    """
    return df[(df['product'] == product) & (df['day'] == day)]

def get_price_data(df: pd.DataFrame, product: str = None, day: int = None) -> pd.DataFrame:
    """
    Get price data with optional filtering by product and/or day.

    Args:
        df (pd.DataFrame): DataFrame containing price data
        product (str, optional): Product name to filter for
        day (int, optional): Day number to filter for

    Returns:
        pd.DataFrame: Filtered price data
    """
    result = df.copy()
    if product:
        result = result[result['product'] == product]
    if day:
        result = result[result['day'] == day]
    if 'timestamp' in result.columns:
        result = result.sort_values('timestamp')
    return result

def get_order_book_data(df: pd.DataFrame, product: str = None, day: int = None) -> pd.DataFrame:
    """
    Get order book data with optional filtering by product and/or day.

    Args:
        df (pd.DataFrame): DataFrame containing price data
        product (str, optional): Product name to filter for
        day (int, optional): Day number to filter for

    Returns:
        pd.DataFrame: Filtered order book data
    """
    result = df.copy()
    if product:
        result = result[result['product'] == product]
    if day:
        result = result[result['day'] == day]
    if 'timestamp' in result.columns:
        result = result.sort_values('timestamp')
    return result

def get_volume_data(df: pd.DataFrame, product: str = None, day: int = None) -> pd.DataFrame:
    """
    Get volume data with optional filtering by product and/or day.

    Args:
        df (pd.DataFrame): DataFrame containing trade data
        product (str, optional): Product name to filter for
        day (int, optional): Day number to filter for

    Returns:
        pd.DataFrame: Filtered volume data
    """
    result = df.copy()
    if product:
        result = result[result['product'] == product]
    if day:
        result = result[result['day'] == day]
    if 'timestamp' in result.columns:
        result = result.sort_values('timestamp')
    return result

def convert_timestamp(df: pd.DataFrame) -> pd.DataFrame:
    return df.assign(t=(df['day'] - 1) * 1_000_000 + df['timestamp']).drop(columns=['day', 'timestamp'])