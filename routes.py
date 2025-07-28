import os
import pandas as pd
import json
import logging
from flask import render_template, request, redirect, url_for, flash, jsonify
from app import app
from data_manager import DataManager
from yahoo_finance_client import YahooFinanceClient
from strategies.simple_moving_average import SimpleMovingAverageStrategy
from strategies.v20_strategy import V20Strategy
from strategies.range_bound_trading import RangeBoundTradingStrategy
from strategies.reverse_head_shoulder import ReverseHeadShoulderStrategy
from strategies.cup_with_handle import CupWithHandleStrategy
from strategies.v10_strategy import V10Strategy
from strategies.lifetime_high_strategy import LifetimeHighStrategy
from strategies.week_low_strategy import WeekLowStrategy

# Configure logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

# Initialize managers
data_manager = DataManager()
yahoo_client = YahooFinanceClient()

# Initialize strategies
strategies = {
    'simple_moving_average': SimpleMovingAverageStrategy(),
    'v20': V20Strategy(),
    'range_bound': RangeBoundTradingStrategy(),
    'reverse_head_shoulder': ReverseHeadShoulderStrategy(),
    'cup_with_handle': CupWithHandleStrategy(),
    'v10': V10Strategy(),
    'lifetime_high': LifetimeHighStrategy(),
    'week_low': WeekLowStrategy()
}


# Template global functions
@app.template_global()
def getSignalBadgeClass(signal):
    """Return Bootstrap badge class for signal type"""
    signal_classes = {
        'Buy': 'bg-success',
        'Sell': 'bg-danger',
        'Watch': 'bg-warning text-dark',
        'Neutral': 'bg-secondary'
    }
    return signal_classes.get(signal, 'bg-secondary')


def determine_overall_signal(signals):
    """Determine overall signal from a list of strategy signals.
    Choose signal with highest count (excluding 'Neutral' unless all are Neutral).
    If there's a tie, resolve by priority: Buy > Sell > Watch.
    """
    if not signals:
        return 'Neutral'

    # Count signals
    counts = {
        'Buy': signals.count('Buy'),
        'Sell': signals.count('Sell'),
        'Watch': signals.count('Watch'),
        'Neutral': signals.count('Neutral')
    }

    # If all are Neutral
    if counts['Neutral'] == len(signals):
        return 'Neutral'

    # Consider only non-neutral signals
    non_neutral_counts = {k: v for k, v in counts.items() if k != 'Neutral'}
    max_count = max(non_neutral_counts.values())

    # Get candidates with max count
    candidates = [signal for signal, count in non_neutral_counts.items() if count == max_count]

    # Resolve tie by priority
    priority = ['Buy', 'Sell', 'Watch']
    for signal in priority:
        if signal in candidates:
            return signal


@app.route('/')
def index():
    """Main dashboard - redirect to user view"""
    return render_template('vivek_singhal_notes.html')


@app.route('/admin/')
def admin():
    """Admin panel for managing stocks"""
    stocks_data = data_manager.get_all_stocks()
    groups = ['V40', 'V40_Next', 'V200', 'Personal_Portfolio']
    return render_template('admin.html', stocks_data=stocks_data, groups=groups)


@app.route('/admin/add_stock', methods=['POST'])
def add_stock():
    """Add a single stock to a group"""
    try:
        group = request.form.get('group')
        stock_code = request.form.get('stock_code', '').strip().upper()

        if not stock_code:
            flash('Stock code is required', 'error')
            return redirect(url_for('admin'))

        # For Personal Portfolio, get additional data
        if group == 'Personal_Portfolio':
            quantity = request.form.get('quantity', 0)
            buy_price = request.form.get('buy_price', 0)

            if not quantity or not buy_price:
                flash('Quantity and Buy Price are required for Personal Portfolio', 'error')
                return redirect(url_for('admin'))

            try:
                quantity = float(quantity)
                buy_price = float(buy_price)
            except ValueError:
                flash('Invalid quantity or buy price format', 'error')
                return redirect(url_for('admin'))

            success = data_manager.add_stock_to_portfolio(stock_code, quantity, buy_price)
        else:
            success = data_manager.add_stock_to_group(stock_code, group)

        if success:
            flash(f'Stock {stock_code} added to {group} successfully!', 'success')
        else:
            flash(f'Failed to add stock {stock_code} to {group}. It may already exist.', 'warning')

    except Exception as e:
        logger.error(f"Error adding stock: {str(e)}")
        flash(f'Error adding stock: {str(e)}', 'error')

    return redirect(url_for('admin'))


@app.route('/admin/delete_stock', methods=['POST'])
def delete_stock():
    """Delete a stock from a group"""
    try:
        group = request.form.get('group')
        stock_code = request.form.get('stock_code')

        success = data_manager.delete_stock_from_group(stock_code, group)

        if success:
            flash(f'Stock {stock_code} deleted from {group} successfully!', 'success')
        else:
            flash(f'Failed to delete stock {stock_code} from {group}', 'error')

    except Exception as e:
        logger.error(f"Error deleting stock: {str(e)}")
        flash(f'Error deleting stock: {str(e)}', 'error')

    return redirect(url_for('admin'))


@app.route('/admin/bulk_upload', methods=['POST'])
def bulk_upload():
    """Bulk upload stocks from Excel file with improved error handling"""
    if 'file' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('admin'))

    file = request.files['file']
    group = request.form.get('group')

    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('admin'))

    if group == 'Personal_Portfolio':
        flash('Bulk upload not allowed for Personal Portfolio', 'error')
        return redirect(url_for('admin'))

    try:
        # Read the Excel file
        df = pd.read_excel(file)

        # Get stock codes from first column, handle different data types
        raw_stock_codes = df.iloc[:, 0].tolist()

        # Clean and filter stock codes
        stock_codes = []
        skipped_codes = []

        for i, code in enumerate(raw_stock_codes):
            if pd.isna(code) or code is None:
                skipped_codes.append(f"Row {i + 1}: Empty/NaN")
                continue

            # Convert to string and clean
            cleaned_code = str(code).strip().upper()

            # Skip if empty, NAN, or contains only spaces/numbers that don't look like stock codes
            if not cleaned_code or cleaned_code in ['NAN', 'NONE', ''] or cleaned_code.isdigit():
                skipped_codes.append(f"Row {i + 1}: {code}")
                continue

            # Remove common prefixes/suffixes that might be in the data
            cleaned_code = cleaned_code.replace('.NS', '').replace('.BSE', '').replace('.BO', '')

            if cleaned_code and len(cleaned_code) >= 2:  # Valid stock codes should be at least 2 characters
                stock_codes.append(cleaned_code)
            else:
                skipped_codes.append(f"Row {i + 1}: {code}")

        if not stock_codes:
            flash('No valid stock codes found in the Excel file. Please check the format.', 'error')
            if skipped_codes[:5]:  # Show first 5 skipped codes
                flash(f'Skipped entries: {", ".join(skipped_codes[:5])}...', 'info')
            return redirect(url_for('admin'))

        success_count = 0
        failed_stocks = []
        duplicate_stocks = []

        for stock_code in stock_codes:
            try:
                result = data_manager.add_stock_to_group(stock_code, group)
                if result:
                    success_count += 1
                else:
                    duplicate_stocks.append(stock_code)
            except Exception as e:
                failed_stocks.append(stock_code)
                logger.error(f"Exception adding {stock_code}: {e}")

        # Provide detailed feedback
        if success_count > 0:
            flash(f'Successfully added {success_count} new stocks to {group}', 'success')

        if duplicate_stocks:
            flash(
                f'{len(duplicate_stocks)} stocks already existed: {", ".join(duplicate_stocks[:5])}{"..." if len(duplicate_stocks) > 5 else ""}',
                'info')

        if failed_stocks:
            flash(
                f'Failed to add {len(failed_stocks)} stocks due to errors: {", ".join(failed_stocks[:3])}{"..." if len(failed_stocks) > 3 else ""}',
                'warning')

        if skipped_codes:
            flash(f'Skipped {len(skipped_codes)} invalid entries from Excel file', 'info')

        if success_count == 0 and not duplicate_stocks:
            flash('No stocks were added. Please check your Excel file format.', 'error')

    except pd.errors.EmptyDataError:
        flash('The Excel file appears to be empty', 'error')
    except pd.errors.ParserError:
        flash('Error reading the Excel file. Please check the file format.', 'error')
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        flash(f'Error processing file: {str(e)}', 'error')

    return redirect(url_for('admin'))


@app.route('/user/')
def user_dashboard():
    """User dashboard for viewing stock data"""
    groups = ['V40', 'V40_Next', 'V200', 'Personal_Portfolio']
    selected_group = request.args.get('group', 'V40')
    time_period = request.args.get('period', '1y')

    stocks_data = data_manager.get_stocks_by_group(selected_group)

    # Calculate strategy signals for each stock
    for stock in stocks_data:
        stock_code = stock['stock_code']
        stock_data = data_manager.get_stock_data(stock_code, time_period)

        if not stock_data.empty:
            # Get signals from all strategies with timeout protection
            strategy_signals = {}
            for strategy_name, strategy in strategies.items():
                try:
                    # Add timeout protection for strategy execution
                    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

                    with ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(strategy.get_signal, stock_data)
                        try:
                            strategy_signal = future.result(timeout=5)  # 5 second timeout
                            strategy_signals[strategy_name] = strategy_signal or 'Neutral'
                        except FuturesTimeout:
                            logger.warning(f"Timeout getting signal for {strategy_name} on {stock_code}")
                            strategy_signals[strategy_name] = 'Neutral'
                        except Exception as e:
                            logger.error(f"Error getting signal for {strategy_name} on {stock_code}: {e}")
                            strategy_signals[strategy_name] = 'Neutral'

                except Exception as e:
                    logger.error(f"Error getting signal for {strategy_name} on {stock_code}: {e}")
                    strategy_signals[strategy_name] = 'Neutral'

            stock['strategy_signals'] = strategy_signals

            # Determine overall signal from applicable strategies
            applicable_signals = []
            for strategy_name, strategy in strategies.items():
                # Check if strategy is applicable to the group
                if hasattr(strategy, 'is_applicable_to_group'):
                    if strategy.is_applicable_to_group(selected_group):
                        applicable_signals.append(strategy_signals.get(strategy_name, 'Neutral'))
                elif hasattr(strategy, 'applicable_groups'):
                    # Fallback: check if strategy has applicable_groups attribute
                    if selected_group in strategy.applicable_groups:
                        applicable_signals.append(strategy_signals.get(strategy_name, 'Neutral'))
                else:
                    # Default: include all strategies that don't have group restrictions
                    applicable_signals.append(strategy_signals.get(strategy_name, 'Neutral'))

            stock['strategy_signal'] = determine_overall_signal(applicable_signals) if applicable_signals else 'Neutral'

            # Add current price and daily change
            current_price = stock_data['Close'].iloc[-1] if len(stock_data) > 0 else 0
            prev_price = stock_data['Close'].iloc[-2] if len(stock_data) > 1 else current_price
            daily_change = ((current_price - prev_price) / prev_price * 100) if prev_price > 0 else 0

            stock['current_price'] = round(current_price, 2)
            stock['daily_change'] = round(daily_change, 2)

            # For Personal Portfolio, add gain/loss and current value
            if selected_group == 'Personal_Portfolio':
                buy_price = stock.get('buy_price', 0)
                quantity = stock.get('quantity', 0)
                if buy_price > 0:
                    gain_loss = ((current_price - buy_price) / buy_price * 100)
                    stock['gain_loss'] = round(gain_loss, 2)
                    stock['current_value'] = round(current_price * quantity, 2)
        else:
            # No stock data available - set default values
            stock['strategy_signals'] = {name: 'Neutral' for name in strategies.keys()}
            stock['strategy_signal'] = 'Neutral'
            stock['current_price'] = 0
            stock['daily_change'] = 0

    return render_template('user_dashboard.html',
                           stocks_data=stocks_data,
                           groups=groups,
                           selected_group=selected_group,
                           time_period=time_period)


@app.route('/stock/<stock_code>')
def stock_detail(stock_code):
    """Detailed view of a single stock"""
    time_period = request.args.get('period', '1y')

    # Get stock data
    stock_data = data_manager.get_stock_data(stock_code, time_period)
    fundamental_data = data_manager.get_fundamental_data(stock_code)

    if stock_data.empty:
        flash(f'No data available for stock {stock_code}', 'error')
        return redirect(url_for('user_dashboard'))

    # Generate strategy analysis for each applicable strategy
    strategy_analysis = {}
    for strategy_name, strategy in strategies.items():
        try:
            analysis = strategy.analyze_stock(stock_data, fundamental_data)
            if analysis:
                strategy_analysis[strategy_name] = analysis
        except Exception as e:
            logger.error(f"Error analyzing {strategy_name} for {stock_code}: {e}")

    return render_template('stock_detail.html',
                           stock_code=stock_code,
                           stock_data=stock_data.to_dict('records'),
                           fundamental_data=fundamental_data,
                           strategy_analysis=strategy_analysis,
                           time_period=time_period)


@app.route('/refresh_data', methods=['POST'])
def refresh_data():
    """Refresh all stock data from Yahoo Finance with enhanced progress tracking"""
    import time

    try:
        start_time = time.time()
        all_stocks = data_manager.get_all_stock_codes()
        success_count = 0
        error_count = 0
        skipped_count = 0

        if not all_stocks:
            flash('No stocks found to refresh', 'warning')
            return redirect(request.referrer or url_for('user_dashboard'))

        logger.info(f"Starting refresh for {len(all_stocks)} stocks")

        # Track progress for each stock
        total_stocks = len(all_stocks)

        for i, stock_code in enumerate(all_stocks, 1):
            try:
                # Log progress every 10 stocks
                if i % 10 == 0 or i == total_stocks:
                    logger.info(f"Processing stock {i}/{total_stocks}: {stock_code}")

                stock_updated = False

                # Fetch data for both 1y and 2y periods
                for period in ['1y', '2y']:
                    try:
                        stock_data = yahoo_client.get_stock_data(stock_code, period)
                        if not stock_data.empty:
                            data_manager.save_stock_data(stock_code, stock_data, period)
                            stock_updated = True
                        else:
                            logger.warning(f"No data returned for {stock_code} - {period}")
                    except Exception as period_error:
                        logger.error(f"Error fetching {period} data for {stock_code}: {period_error}")
                        continue

                # Fetch fundamental data
                try:
                    fundamental_data = yahoo_client.get_fundamental_data(stock_code)
                    if fundamental_data:
                        data_manager.save_fundamental_data(stock_code, fundamental_data)
                        stock_updated = True
                except Exception as fund_error:
                    logger.warning(f"Error fetching fundamental data for {stock_code}: {fund_error}")

                if stock_updated:
                    success_count += 1
                else:
                    skipped_count += 1
                    logger.warning(f"No data updated for {stock_code}")

            except Exception as e:
                logger.error(f"Error refreshing {stock_code}: {e}")
                error_count += 1
                continue

        end_time = time.time()
        duration = round(end_time - start_time, 2)

        # Prepare success message
        messages = []
        if success_count > 0:
            messages.append(f'Successfully refreshed {success_count} stocks')

        if skipped_count > 0:
            messages.append(f'{skipped_count} stocks had no new data')

        if error_count > 0:
            messages.append(f'{error_count} stocks failed to refresh')

        # Create comprehensive flash message
        if success_count > 0:
            main_message = f'Data refresh completed in {duration}s. {" | ".join(messages)}'
            flash(main_message, 'success')
        elif error_count == total_stocks:
            flash(f'Refresh failed for all {total_stocks} stocks. Please check your internet connection.', 'error')
        else:
            flash(f'Partial refresh completed in {duration}s. {" | ".join(messages)}', 'warning')

        logger.info(
            f"Refresh completed: {success_count} success, {error_count} errors, {skipped_count} skipped in {duration}s")

    except Exception as e:
        logger.error(f"Critical refresh error: {e}")
        flash(f'Critical error during refresh: {str(e)}', 'error')

    return redirect(request.referrer or url_for('user_dashboard'))


@app.route('/api/refresh_status')
def refresh_status():
    """API endpoint to check refresh status (for future async implementation)"""
    # This could be enhanced later to track refresh progress in real-time
    # For now, just return a simple status
    return jsonify({
        'status': 'ready',
        'message': 'Refresh functionality is available'
    })


@app.route('/api/chart_data/<stock_code>')
def get_chart_data(stock_code):
    """API endpoint to get chart data for a stock"""
    time_period = request.args.get('period', '1y')
    strategy_name = request.args.get('strategy', 'simple_moving_average')

    stock_data = data_manager.get_stock_data(stock_code, time_period)

    if stock_data.empty:
        return jsonify({'error': 'No data available'})

    # Get strategy-specific annotations and overlays
    strategy = strategies.get(strategy_name)
    chart_config = {}

    if strategy:
        try:
            chart_config = strategy.get_chart_config(stock_data)
        except Exception as e:
            logger.error(f"Error getting chart config for {strategy_name}: {e}")

    # Prepare data for Plotly
    chart_data = {
        'dates': stock_data.index.strftime('%Y-%m-%d').tolist(),
        'open': stock_data['Open'].tolist(),
        'high': stock_data['High'].tolist(),
        'low': stock_data['Low'].tolist(),
        'close': stock_data['Close'].tolist(),
        'volume': stock_data['Volume'].tolist(),
        'config': chart_config
    }

    return jsonify(chart_data)