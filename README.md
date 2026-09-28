# 🚀 Sales Aura

### PyQt6 + MySQL Business Management, Invoicing & Sales Prediction System

**Sales Aura** is a modern desktop business management and invoicing application built with **Python, PyQt6 and MySQL**.

It brings sales, purchasing, quotations, invoicing, customer management, accounts, inventory-related operations, reports and **sales prediction** together in a single desktop application.

The project is designed for small and medium-sized businesses that need a practical desktop solution for managing their day-to-day sales and billing operations while also turning historical sales data into actionable insights.

---

## ✨ Key Features

### 🧾 Invoice Management

* Tax Invoice generation and management
* Proforma Invoice
* Quotation
* Quick Quotation
* Purchase Invoice
* Invoice editing and deletion
* Invoice viewing
* Print Preview
* PDF-ready invoice printing
* Financial-year based invoice numbering
* GST / tax calculation support
* Automatic subtotal, tax and grand-total calculations

---

### 👥 Customer & Supplier Management

Manage customers and suppliers from a centralized interface.

* Add customers
* Edit customer information
* Delete customers
* Customer information pages
* Supplier management
* Customer/Supplier classification
* Searchable customer selection
* Customer transaction history
* Supplier transaction history

---

### 📦 Product Management

Maintain your product catalog from within the application.

* Product creation
* Product editing
* Product deletion
* Product information
* Product pricing
* HSN code support
* Product-related transaction information

---

### 💰 Accounts & Ledger

Sales Aura includes an integrated account and ledger system for tracking business transactions.

* Customer accounts
* Supplier accounts
* Opening balance
* Credit transactions
* Debit transactions
* Closing balance
* Ledger view
* Financial-year based accounting
* Transaction history
* Account summaries

---

### 📊 Sales & Business Reports

Analyze your business data through dedicated reporting pages.

Supported reporting areas include:

* Sales reports
* Purchase reports
* Quotation reports
* Transaction reports
* Account reports
* Customer-related reports
* Product-related information
* Financial-year based reporting
* Export-ready report data

---

### 🤖 Sales Prediction

One of the main features of Sales Aura is its **Sales Prediction** module.

The system uses historical sales information to help transform business transaction data into useful insights.

The module is designed to support:

* Historical sales analysis
* Sales trends
* Sales forecasting
* Prediction dashboards
* Data-driven business analysis
* Future sales planning

> Sales prediction results should be treated as analytical estimates and not guaranteed future outcomes.

---

### 📈 Dashboard & Analytics

The dashboard provides an overview of important business information.

Depending on the configured data, the dashboard can provide information related to:

* Sales turnover
* Purchase activity
* Tax/GST information
* Business transactions
* Customer activity
* Product activity
* Sales trends
* Prediction insights

---

### 🔎 Smart DataTables-Style Interfaces

List pages provide a DataTables-inspired experience.

Features include:

* Search
* Pagination
* First / Previous / Next / Last navigation
* Page numbers
* Rows per page
* 10 / 25 / 50 / 100 / All entries
* Entry counters
* Filtered totals
* Visible-page totals
* Fast client-side page rendering

---

### 🖨️ Printing & PDF

Sales Aura provides printing functionality for business documents.

Supported document workflows include:

* Tax Invoice
* Proforma Invoice
* Quotation
* Quick Quotation
* Purchase Invoice

Documents can be opened through print preview and prepared for PDF/physical printing.

---

## 🏗️ Application Modules

| Module              | Description                          |
| ------------------- | ------------------------------------ |
| 🏠 Dashboard        | Business overview and analytics      |
| 👥 Clients          | Customer management                  |
| 🏭 Suppliers        | Supplier management                  |
| 📦 Products         | Product catalog                      |
| 🧾 Tax Invoice      | Sales invoice management             |
| 📄 Proforma         | Proforma invoice management          |
| 💬 Quotation        | Quotation management                 |
| ⚡ Quick Quotation   | Fast quotation workflow              |
| 🛒 Purchase         | Purchase invoice management          |
| 💳 Transactions     | Payment/transaction management       |
| 📚 Accounts         | Account and ledger management        |
| 📊 Reports          | Sales, purchase and business reports |
| 🤖 Sales Prediction | Sales analysis and forecasting       |
| ⚙️ Settings         | Application/company settings         |

---

## 🛠️ Technology Stack

### Desktop Application

* **Python 3**
* **PyQt6**
* **PyMySQL**

### Database

* **MySQL / MariaDB**

### Application Architecture

* PyQt6 desktop UI
* Modular page architecture
* MySQL database layer
* Reusable utility functions
* Invoice/document rendering
* Financial-year based business logic

---

## 📁 Project Structure

```text
pyqt_app/
│
├── database/
│   └── db_manager.py
│
├── dist/
│   └── img/
│
├── tools/
│   └── make_brand_logo.py
│
├── ui/
│   ├── pages/
│   │   ├── accounts_page.py
│   │   ├── dashboard_page.py
│   │   ├── invoice_pages.py
│   │   ├── master_pages.py
│   │   ├── quickquote_page.py
│   │   ├── reports_page.py
│   │   ├── sales_prediction_page.py
│   │   ├── settings_page.py
│   │   └── transaction_page.py
│   │
│   ├── login_window.py
│   ├── main_window.py
│   ├── splash_screen.py
│   ├── app_icon.py
│   └── icons.py
│
├── utils/
│   ├── helpers.py
│   └── invoice_print.py
│
├── config.py
├── db.sql
├── main.py
├── requirements.txt
├── smoke_test.py
└── README.md
```

---

# 🚀 Installation

## 1. Clone the Repository

```bash
git clone https://github.com/reputed-artist/PYQT-MYSQL-INVOICE-QUOTATION-PROFORMA-PURCHASE-INVOICE-MANAGEMENT-WITH-SALES-PREDICTION-SYSTEM.git
```

Move into the project directory:

```bash
cd PYQT-MYSQL-INVOICE-QUOTATION-PROFORMA-PURCHASE-INVOICE-MANAGEMENT-WITH-SALES-PREDICTION-SYSTEM
```

---

## 2. Create a Virtual Environment

Windows:

```powershell
python -m venv venv
```

Activate it:

```powershell
venv\Scripts\activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

The repository already contains a `requirements.txt` file for the Python dependencies.

---

# 🗄️ Database Setup

Sales Aura requires a MySQL/MariaDB database.

### 1. Create a database

For example:

```sql
CREATE DATABASE db;
```

### 2. Import the database

Import:

```text
db.sql
```

using phpMyAdmin, MySQL Workbench or the MySQL command line.

Example:

```bash
mysql -u root -p db < db.sql
```

---

# ⚙️ Database Configuration

Update the database configuration in:

```text
config.py
```

Example:

```python
DB_HOST = "localhost"
DB_NAME = "db"
DB_USER = "root"
DB_PASSWORD = ""
```

Adjust these values according to your MySQL/MariaDB installation.

---

# ▶️ Run Sales Aura

Start the application using:

```bash
python main.py
```

The application will launch the Sales Aura desktop interface.

---

# 🔐 Login

```plaintext
Email: admin@gmail.com
Password: admin@123
```

> **Security:** Do not publish real production credentials in this repository. Change any default development password before using the application in a production environment.

---

# 🧪 Testing

A smoke test is included to verify that the application can start and construct the major application pages.

Run:

```bash
python main.py
```

The test covers application startup, login/database interaction and page construction.

---

# 🎨 Sales Aura Branding

Sales Aura includes its own application branding and icon system.

The application icon can be generated using:

```bash
python tools/make_brand_logo.py
```

To generate preview sizes:

```bash
python tools/make_brand_logo.py --preview %TEMP%\aura
```

The application supports branded icons across:

* Splash screen
* Login window
* Main window
* Dialogs
* Message boxes
* Print previews
* Information pages

---

# 📑 Supported Business Documents

Sales Aura currently supports the following document workflows:

```text
Tax Invoice
     │
     ├── Create
     ├── View
     ├── Edit
     ├── Print
     └── Delete

Proforma Invoice
     │
     ├── Create
     ├── View
     ├── Edit
     └── Print

Quotation
     │
     ├── Create
     ├── View
     ├── Edit
     └── Print

Quick Quotation
     │
     ├── Create
     ├── View
     └── Print

Purchase Invoice
     │
     ├── Create
     ├── View
     ├── Edit
     └── Print
```

---


---

# 🧠 Sales Intelligence

Sales Aura is not limited to traditional billing.

The long-term goal of the project is to combine:

```text
Business Transactions
        ↓
Historical Sales Data
        ↓
Analytics
        ↓
Sales Trends
        ↓
Prediction
        ↓
Business Insights
```

This makes the system useful not only for recording transactions but also for understanding business performance.

---



# 🤝 Contributing

Contributions, suggestions and bug reports are welcome.


# 📜 License

This project is licensed under the **MIT License** unless otherwise specified in the repository.


# 👨‍💻 Developer

Developed by **Tejas Chavda**

**Tejaschavda2020@gmail.com**

---

# ⭐ Support the Project

If you find **Sales Aura** useful:

⭐ Star the repository on GitHub

🐛 Report bugs

💡 Suggest improvements

🔧 Contribute code

📢 Share the project with other developers and businesses

---


### Sales Aura

> **Invoices · Insights · Intelligence**
