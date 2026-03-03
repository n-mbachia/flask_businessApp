# 📁 **Scripts Directory Structure**

This directory contains administrative and utility scripts for the business intelligence system.

## 🗂️ **Directory Structure**

```
scripts/
├── admin/
│   └── bi_admin.py          # Comprehensive BI admin CLI
├── utils/
│   └── (future utilities)
├── legacy/
│   ├── check_orders.py       # Original simple order checker
│   └── check_orders_status.py # Original detailed order checker
└── requirements.txt          # Script dependencies
```

## 🚀 **New Admin CLI Usage**

### **Installation**
```bash
# Install script dependencies
pip install -r scripts/requirements.txt

# Make script executable
chmod +x scripts/admin/bi_admin.py
```

### **Available Commands**

#### **📊 Order Reports**
```bash
# Basic order status report
python scripts/admin/bi_admin.py orders

# Detailed order report with customer info
python scripts/admin/bi_admin.py orders --detailed
```

#### **👥 Customer Analysis**
```bash
# Top customers by revenue and order count
python scripts/admin/bi_admin.py customers
```

#### **📦 Product Performance**
```bash
# Top products by revenue and units sold
python scripts/admin/bi_admin.py products
```

#### **🏥 System Health**
```bash
# Complete system health overview
python scripts/admin/bi_admin.py health
```

#### **📈 Recent Activity**
```bash
# Last 7 days activity (default)
python scripts/admin/bi_admin.py activity

# Last 30 days activity
python scripts/admin/bi_admin.py activity --days 30
```

#### **📋 Complete Dashboard**
```bash
# Comprehensive report with all sections
python scripts/admin/bi_admin.py dashboard
```

## 🔄 **Migration from Legacy Scripts**

### **Old Scripts (Moved to Legacy)**
- `check_orders.py` → `scripts/legacy/check_orders.py`
- `check_orders_status.py` → `scripts/legacy/check_orders_status.py`

### **New Equivalent Commands**
```bash
# Old: python check_orders.py
# New: python scripts/admin/bi_admin.py orders

# Old: python check_orders_status.py  
# New: python scripts/admin/bi_admin.py orders --detailed
```

## 🎯 **Features of New Admin CLI**

### **📊 Enhanced Reporting**
- **Tabulated Output**: Clean, formatted tables
- **Multiple Metrics**: Revenue, counts, averages
- **Sorting & Filtering**: Top N results
- **Date Ranges**: Flexible time periods

### **🏥 System Health Monitoring**
- **Database Statistics**: Orders, customers, products
- **Revenue Metrics**: Total, average, trends
- **Status Breakdown**: Pending, completed, cancelled
- **Performance Indicators**: Key business metrics

### **👥 Customer Intelligence**
- **Top Customers**: By revenue and order frequency
- **Customer Segments**: High-value vs regular
- **Purchase Patterns**: Order history analysis
- **Contact Information**: Email and name details

### **📦 Product Analytics**
- **Best Sellers**: Revenue and volume metrics
- **SKU Tracking**: Product identification
- **Inventory Insights**: Sales performance
- **Revenue Analysis**: Product profitability

### **📈 Activity Monitoring**
- **Recent Orders**: Last N days activity
- **Status Tracking**: Order lifecycle monitoring
- **Customer Activity**: Recent purchase behavior
- **Trend Analysis**: Business activity patterns

## 🛠️ **Technical Improvements**

### **🔧 Better Code Organization**
- **CLI Framework**: Click-based command structure
- **Modular Design**: Separate reporting classes
- **Error Handling**: Robust exception management
- **Configuration**: Flexible parameter options

### **📊 Enhanced Output**
- **Tabulated Tables**: Clean, readable format
- **Monetary Formatting**: Proper currency display
- **Data Truncation**: Handle long text fields
- **Color Coding**: Visual status indicators

### **🚀 Performance**
- **Optimized Queries**: Efficient database access
- **Batch Operations**: Reduced database calls
- **Memory Efficient**: Large dataset handling
- **Fast Execution**: Quick report generation

## 📋 **Usage Examples**

### **Daily Business Review**
```bash
# Quick morning check
python scripts/admin/bi_admin.py dashboard

# Focus on recent activity
python scripts/admin/bi_admin.py activity --days 1

# Check system health
python scripts/admin/bi_admin.py health
```

### **Weekly Analysis**
```bash
# Comprehensive weekly report
python scripts/admin/bi_admin.py dashboard

# Customer performance focus
python scripts/admin/bi_admin.py customers

# Product sales review
python scripts/admin/bi_admin.py products
```

### **Monthly Reporting**
```bash
# Full month overview
python scripts/admin/bi_admin.py activity --days 30

# Detailed order analysis
python scripts/admin/bi_admin.py orders --detailed

# System health check
python scripts/admin/bi_admin.py health
```

## 🔄 **Integration with Business Intelligence**

The new admin CLI integrates seamlessly with your business intelligence system:

- **📊 Analytics Data**: Uses same database models and queries
- **🔮 Predictive Insights**: Can be extended with ML predictions
- **🔄 Real-time Data**: Shows current system state
- **🛡️ Security**: Uses same authentication and authorization
- **⚡ Performance**: Optimized for large datasets

## 🚀 **Future Enhancements**

### **Planned Features**
- **📈 Trend Analysis**: Historical trend reporting
- **🎯 Goal Tracking**: Business KPI monitoring
- **📧 Email Reports**: Automated report delivery
- **🌐 Web Interface**: Browser-based admin panel
- **📱 Mobile Support**: Mobile-optimized reports

### **Integration Points**
- **🔮 Predictive Analytics**: Add forecast reports
- **📊 Dashboard Integration**: Link to web dashboard
- **🔄 Real-time Updates**: Live monitoring capabilities
- **📊 Custom Reports**: User-configurable reports

**This new admin CLI provides a comprehensive, professional replacement for the legacy order checking scripts!** 🎯
