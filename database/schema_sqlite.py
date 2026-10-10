"""
SQLite table schema definitions for local storage.
"""

SQLITE_TABLES = [
    ("account", """
        CREATE TABLE IF NOT EXISTS account (
            aid INTEGER PRIMARY KEY AUTOINCREMENT,
            cid INTEGER NOT NULL,
            acc_type INTEGER NOT NULL,
            opening_bal REAL NOT NULL,
            created DATE NOT NULL
        )
    """),
    ("acc_type", """
        CREATE TABLE IF NOT EXISTS acc_type (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL
        )
    """),
    ("admin", """
        CREATE TABLE IF NOT EXISTS admin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            qualification TEXT NOT NULL,
            location TEXT NOT NULL,
            skills TEXT NOT NULL,
            c_name TEXT NOT NULL,
            c_add TEXT NOT NULL,
            profession TEXT NOT NULL,
            mob TEXT NOT NULL,
            gst TEXT NOT NULL,
            pan TEXT NOT NULL,
            picture TEXT NOT NULL,
            picturelogo TEXT NOT NULL
        )
    """),
    ("bankdetails", """
        CREATE TABLE IF NOT EXISTS bankdetails (
            bid INTEGER PRIMARY KEY AUTOINCREMENT,
            bname TEXT NOT NULL,
            ac TEXT NOT NULL,
            ifsc TEXT NOT NULL,
            branch TEXT NOT NULL
        )
    """),
    ("client", """
        CREATE TABLE IF NOT EXISTS client (
            cid INTEGER PRIMARY KEY AUTOINCREMENT,
            c_name TEXT NOT NULL,
            c_add TEXT NOT NULL,
            mob TEXT NOT NULL,
            country TEXT NOT NULL,
            gst TEXT NOT NULL,
            email TEXT,
            c_type TEXT NOT NULL,
            u_type INTEGER NOT NULL,
            created DATE NOT NULL
        )
    """),
    ("clienttype", """
        CREATE TABLE IF NOT EXISTS clienttype (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL
        )
    """),
    ("delivery_addresses", """
        CREATE TABLE IF NOT EXISTS delivery_addresses (
            delid INTEGER PRIMARY KEY AUTOINCREMENT,
            invid TEXT NOT NULL,
            name TEXT NOT NULL,
            address TEXT NOT NULL,
            mob TEXT NOT NULL
        )
    """),
    ("fd", """
        CREATE TABLE IF NOT EXISTS fd (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fdissueddate DATE,
            fdholder TEXT NOT NULL,
            fdofbank TEXT NOT NULL,
            principleamt INTEGER NOT NULL,
            nodays TEXT NOT NULL,
            intrate TEXT NOT NULL,
            intamt TEXT NOT NULL,
            finalamt REAL NOT NULL,
            maturitydate DATE NOT NULL,
            fdentrydate DATETIME NOT NULL
        )
    """),
    ("fest", """
        CREATE TABLE IF NOT EXISTS fest (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            fest_name TEXT NOT NULL,
            gifs TEXT NOT NULL
        )
    """),
    ("invtest", """
        CREATE TABLE IF NOT EXISTS invtest (
            orderno INTEGER PRIMARY KEY AUTOINCREMENT,
            orderid TEXT NOT NULL,
            item_name TEXT NOT NULL,
            item_desc TEXT,
            hsn INTEGER,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            total REAL NOT NULL
        )
    """),
    ("invtest2", """
        CREATE TABLE IF NOT EXISTS invtest2 (
            invid TEXT PRIMARY KEY,
            cid INTEGER NOT NULL,
            orderid TEXT NOT NULL,
            totalitems INTEGER NOT NULL,
            subtotal REAL NOT NULL,
            taxrate REAL NOT NULL,
            taxamount REAL NOT NULL,
            totalamount REAL NOT NULL,
            created DATE NOT NULL
        )
    """),
    ("paidhistory", """
        CREATE TABLE IF NOT EXISTS paidhistory (
            pay_id TEXT PRIMARY KEY,
            cid TEXT NOT NULL,
            amount REAL NOT NULL,
            bank TEXT NOT NULL,
            dateofpayment DATE NOT NULL,
            purpose TEXT NOT NULL,
            created DATETIME NOT NULL
        )
    """),
    ("products", """
        CREATE TABLE IF NOT EXISTS products (
            p_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            hsn INTEGER,
            description TEXT,
            p_type TEXT NOT NULL,
            cattype TEXT,
            img_loc TEXT,
            techs TEXT,
            created DATE NOT NULL
        )
    """),
    ("protest", """
        CREATE TABLE IF NOT EXISTS protest (
            orderno INTEGER PRIMARY KEY AUTOINCREMENT,
            orderid TEXT NOT NULL,
            item_name TEXT NOT NULL,
            item_desc TEXT,
            hsn INTEGER,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            total REAL NOT NULL
        )
    """),
    ("protest2", """
        CREATE TABLE IF NOT EXISTS protest2 (
            invid TEXT PRIMARY KEY,
            cid INTEGER NOT NULL,
            orderid TEXT NOT NULL,
            totalitems INTEGER NOT NULL,
            subtotal REAL NOT NULL,
            taxrate REAL NOT NULL,
            taxamount REAL NOT NULL,
            totalamount REAL NOT NULL,
            created DATE NOT NULL
        )
    """),
    ("purchaseinv", """
        CREATE TABLE IF NOT EXISTS purchaseinv (
            orderno INTEGER PRIMARY KEY AUTOINCREMENT,
            orderid TEXT NOT NULL,
            item_name TEXT NOT NULL,
            item_desc TEXT,
            hsn INTEGER,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            total REAL NOT NULL
        )
    """),
    ("purchaseinv2", """
        CREATE TABLE IF NOT EXISTS purchaseinv2 (
            nid INTEGER PRIMARY KEY AUTOINCREMENT,
            invid TEXT NOT NULL,
            cid INTEGER NOT NULL,
            invdate DATE NOT NULL,
            orderid TEXT NOT NULL,
            totalitems INTEGER NOT NULL,
            subtotal REAL NOT NULL,
            taxrate REAL NOT NULL,
            taxamount REAL NOT NULL,
            totalamount REAL NOT NULL,
            created DATETIME NOT NULL
        )
    """),
    ("quickquote", """
        CREATE TABLE IF NOT EXISTS quickquote (
            sr_no INTEGER PRIMARY KEY AUTOINCREMENT,
            q_id TEXT NOT NULL,
            p_id INTEGER NOT NULL,
            mob TEXT NOT NULL,
            quantity TEXT NOT NULL,
            price REAL NOT NULL,
            subtotal REAL NOT NULL,
            gst REAL NOT NULL,
            total REAL NOT NULL,
            created DATE NOT NULL
        )
    """),
    ("quote", """
        CREATE TABLE IF NOT EXISTS quote (
            orderno INTEGER PRIMARY KEY AUTOINCREMENT,
            orderid TEXT NOT NULL,
            item_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            total REAL NOT NULL
        )
    """),
    ("quote2", """
        CREATE TABLE IF NOT EXISTS quote2 (
            invid TEXT PRIMARY KEY,
            cid INTEGER NOT NULL,
            orderid TEXT NOT NULL,
            totalitems INTEGER NOT NULL,
            subtotal REAL NOT NULL,
            taxrate REAL NOT NULL,
            taxamount REAL NOT NULL,
            totalamount REAL NOT NULL,
            created DATE NOT NULL,
            note TEXT NOT NULL
        )
    """),
    ("techsps", """
        CREATE TABLE IF NOT EXISTS techsps (
            tid INTEGER PRIMARY KEY AUTOINCREMENT,
            p_id INTEGER NOT NULL,
            img_loc TEXT,
            techs TEXT,
            subcat TEXT
        )
    """),
]

SECONDARY_INDEXES = [
    "CREATE INDEX IF NOT EXISTS ix_invtest_orderid ON invtest (orderid)",
    "CREATE INDEX IF NOT EXISTS ix_invtest2_orderid ON invtest2 (orderid)",
    "CREATE INDEX IF NOT EXISTS ix_invtest2_created ON invtest2 (created)",
    "CREATE INDEX IF NOT EXISTS ix_invtest2_cid ON invtest2 (cid)",
    "CREATE INDEX IF NOT EXISTS ix_products_name ON products (name)",
    "CREATE INDEX IF NOT EXISTS ix_protest_orderid ON protest (orderid)",
    "CREATE INDEX IF NOT EXISTS ix_protest2_orderid ON protest2 (orderid)",
    "CREATE INDEX IF NOT EXISTS ix_protest2_cid ON protest2 (cid)",
    "CREATE INDEX IF NOT EXISTS ix_quickquote_pid ON quickquote (p_id)",
    "CREATE INDEX IF NOT EXISTS ix_purchaseinv2_orderid ON purchaseinv2 (orderid)",
    "CREATE INDEX IF NOT EXISTS ix_purchaseinv2_cid ON purchaseinv2 (cid)",
    "CREATE INDEX IF NOT EXISTS ix_purchaseinv2_invdate ON purchaseinv2 (invdate)",
    "CREATE INDEX IF NOT EXISTS ix_quote2_orderid ON quote2 (orderid)",
    "CREATE INDEX IF NOT EXISTS ix_quote2_cid ON quote2 (cid)",
    "CREATE INDEX IF NOT EXISTS ix_paidhistory_cid ON paidhistory (cid)",
    "CREATE INDEX IF NOT EXISTS ix_paidhistory_dop ON paidhistory (dateofpayment)",
    "CREATE INDEX IF NOT EXISTS ix_techsps_pid ON techsps (p_id)",
]
