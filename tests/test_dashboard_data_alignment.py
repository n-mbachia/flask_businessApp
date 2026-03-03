"""Regression test ensuring dashboard chart data and briefs share the same date window."""

from datetime import datetime, timedelta

from app.routes.main import _prepare_chart_data, _build_dashboard_briefs


def _sample_profit_trends(months: int = 3):
    """Helper to build deterministic profit trend payloads."""
    now = datetime.utcnow()
    monthly = []
    months_list = []

    for offset in range(months):
        target = now - timedelta(days=30 * (months - 1 - offset))
        month_str = target.strftime('%Y-%m')
        label = target.strftime('%b %Y')
        monthly.append({
            'month': month_str,
            'label': label,
            'revenue': 10000 + offset * 1000,
            'gross_margin': 35.0,
            'net_margin': 25.0,
            'orders': 10 + offset,
            'profit': 1500 + offset * 100
        })
        months_list.append(label)

    return {
        'months': months_list,
        'monthly': monthly
    }


def test_chart_data_and_briefs_share_window():
    """Ensure chart data and briefs derive from the same date range inputs."""
    profit_trends = _sample_profit_trends()
    cash_flow_trends = [
        {'label': profit_trends['months'][i], 'month': entry['month'],
         'cash_in': 12000 + i * 500, 'cash_out': 8000 + i * 200,
         'operating_cash_flow': 4000 + i * 300}
        for i, entry in enumerate(profit_trends['monthly'])
    ]

    metrics = {
        'revenue': {
            'total_revenue': 15000.0,
            'revenue_growth': 12.5,
            'average_order_value': 250.0,
            'recurring_revenue': 2000.0,
            'customer_count': 50
        },
        'expenses': {
            'total_expenses': 8000.0,
            'expense_breakdown': [
                {'category': 'Rent', 'amount': 2000},
                {'category': 'Marketing', 'amount': 1000}
            ]
        },
        'profitability': {
            'net_profit': 7000.0,
            'net_margin': 35.0,
            'gross_profit': 9000.0,
            'operating_profit': 7500.0
        },
        'cash_flow': {
            'operating_cash_flow': cash_flow_trends[-1]['operating_cash_flow'],
            'cash_in': cash_flow_trends[-1]['cash_in'],
            'cash_out': cash_flow_trends[-1]['cash_out'],
            'cash_burn_rate': 2200.0,
            'runway': 4.5
        },
        'working_capital': {
            'current_assets': 20000.0,
            'current_liabilities': 8000.0,
            'working_capital': 12000.0,
            'current_ratio': 2.5,
            'quick_ratio': 1.8,
            'inventory_turnover': 5.0,
            'days_sales_outstanding': 18.0
        }
    }
    top_products = [
        {'name': 'Product X', 'profit': 2500.0, 'margin': 40.0},
        {'name': 'Product Y', 'profit': 1800.0, 'margin': 30.0}
    ]

    chart_data = _prepare_chart_data(metrics, profit_trends, top_products, cash_flow_trends)
    briefs = _build_dashboard_briefs(metrics, profit_trends, cash_flow_trends, top_products, latest_label=chart_data.get('latest_label'))

    # Chart labels should line up exactly with the cash flow trend labels provided
    expected_labels = [entry['label'] for entry in cash_flow_trends]
    assert chart_data['cashflow_trend']['labels'] == expected_labels

    revenue_brief = next(b for b in briefs if b['id'] == 'revenue-brief')
    assert revenue_brief['badge'] == chart_data['latest_label']

    assert chart_data.get('window_labels') == profit_trends['months']

    cash_brief = next(b for b in briefs if b['id'] == 'cashflow-brief')
    prev = cash_flow_trends[-2]
    latest = cash_flow_trends[-1]
    assert cash_brief['trend'] == latest['operating_cash_flow'] - prev['operating_cash_flow']
