-- =====================================================================
-- CODETECH ENGINEERS — SQLITE DATABASE DUMP (with cattype)
-- Usage:  sqlite3 db.sqlite < sqlite_dump.sql
-- =====================================================================

PRAGMA foreign_keys = OFF;
BEGIN TRANSACTION;

-- =====================================================================
-- LOOKUP TABLES
-- =====================================================================

CREATE TABLE "acc_type" (
  "id"   INTEGER PRIMARY KEY AUTOINCREMENT,
  "type" TEXT NOT NULL
);
INSERT INTO "acc_type" ("id","type") VALUES
(0,'Customer'),
(1,'Supplier'),
(2,'Dual (Cust/Sup)');

CREATE TABLE "clienttype" (
  "id"   INTEGER PRIMARY KEY AUTOINCREMENT,
  "type" TEXT NOT NULL
);
INSERT INTO "clienttype" ("id","type") VALUES
(1,'IGST'),
(2,'Loc');

-- =====================================================================
-- ADMIN / COMPANY
-- =====================================================================

CREATE TABLE "admin" (
  "id"            INTEGER PRIMARY KEY AUTOINCREMENT,
  "username"      TEXT NOT NULL,
  "password"      TEXT NOT NULL,
  "name"          TEXT NOT NULL,
  "email"         TEXT NOT NULL,
  "qualification" TEXT NOT NULL,
  "location"      TEXT NOT NULL,
  "skills"        TEXT NOT NULL,
  "c_name"        TEXT NOT NULL,
  "c_add"         TEXT NOT NULL,
  "profession"    TEXT NOT NULL,
  "mob"           TEXT NOT NULL,
  "gst"           TEXT NOT NULL,
  "pan"           TEXT NOT NULL,
  "picture"       TEXT NOT NULL,
  "picturelogo"   TEXT NOT NULL
);
INSERT INTO "admin" VALUES
(1,'admin@gmail.com','admin@123','Tejas Chavda','info@codetechengineers.in',
 'M-Tech at LJ University','Ahmedabad, Gujarat','["test ,from"]',
 'CodeTech Engineers',
 'A 4/1 Suryanagar Society, Jawahar Chowk, Maninagar, Ahmedabad - 380008',
 'Manufacturer of Batch Coding Machines',
 '+91-9737691234 / +91-7600158240','24AVVPC8158M1ZV','AVVPC8158M',
 '1738680148_07cbe5986e43c596a9d7.jpeg','1738682224_ae94bb2586482adfce76.png');

CREATE TABLE "bankdetails" (
  "bid"    INTEGER PRIMARY KEY AUTOINCREMENT,
  "bname"  TEXT NOT NULL,
  "ac"     TEXT NOT NULL,
  "ifsc"   TEXT NOT NULL,
  "branch" TEXT NOT NULL
);
INSERT INTO "bankdetails" VALUES
(1,'ICICI Bank','6424555555211','ICIC0001223','Maninagar Branch, Ahmedabad');

-- =====================================================================
-- CLIENTS
-- =====================================================================

CREATE TABLE "client" (
  "cid"     INTEGER PRIMARY KEY AUTOINCREMENT,
  "c_name"  TEXT NOT NULL,
  "c_add"   TEXT NOT NULL,
  "mob"     TEXT NOT NULL,
  "country" TEXT NOT NULL,
  "gst"     TEXT NOT NULL,
  "email"   TEXT,
  "c_type"  TEXT NOT NULL,
  "u_type"  INTEGER NOT NULL,
  "created" TEXT NOT NULL
);
INSERT INTO "client" VALUES
(1,'Jaya Enterprises','Plot 12, GIDC Maninagar, Ahmedabad - 380008','+91-9875003590','India','24AABCJ1234M1Z5','accounts@jayaenterprises.in','Loc',0,'2023-08-11'),
(2,'Gamer Packaging Pvt Ltd','Andheri MIDC, Mumbai - 400093','+91-9820033591','India','27AABCG5678N1Z2','purchase@gamerpack.co.in','IGST',0,'2023-09-05'),
(3,'Diamond Foods Ltd','Peenya Industrial Area, Bengaluru - 560058','+91-9880016240','India','29AABCD9012P1Z8','procurement@diamondfoods.in','IGST',0,'2023-10-18'),
(4,'Random India Industries','Auto Nagar, Visakhapatnam - 530012','+91-9848023590','India','37AABCR3456Q1Z4','info@randomindia.co.in','IGST',0,'2023-11-02'),
(5,'Cyan Pharma Ltd','Lower Parel, Mumbai - 400013','+91-9820046240','India','27AABCC7890R1Z1','purchase@cyanpharma.com','IGST',0,'2023-12-14'),
(6,'Code Maninagar Retail','Kankaria Road, Ahmedabad - 380008','+91-7600158245','India','24AABCC2345S1Z9','sales@codemaninagar.in','Loc',0,'2024-01-08'),
(7,'Simon Traders','Nehru Place, New Delhi - 110019','+91-9810016240','India','07AABCS6789T1Z3','simon.traders@gmail.com','IGST',0,'2024-02-15'),
(8,'Amplify Beverages','HSR Layout, Bengaluru - 560102','+91-9880061230','India','29AABCA1234U1Z7','accounts@amplifybev.in','IGST',0,'2024-03-20'),
(9,'Second Name Industries','Bhiwandi, Maharashtra - 421302','+91-9820076240','India','27AABCS5678V1Z5','contact@secondname.co.in','IGST',0,'2024-04-11'),
(10,'Third Co Packaging','Chakan MIDC, Pune - 410501','+91-9822019537','India','27AABCT9012W1Z8','info@thirdco.in','IGST',0,'2024-05-06'),
(11,'SED Logistics','Kalamboli, Navi Mumbai - 410218','+91-9875003590','India','27AABCS3456X1Z2','ops@sedlogistics.in','IGST',0,'2024-06-19'),
(12,'Demo Industries','Jogeshwari, Mumbai - 400060','+91-7600158240','India','27AABCD7890Y1Z6','demo@industries.in','IGST',0,'2024-07-03'),
(13,'Jai Plastics','Odhav GIDC, Ahmedabad - 382415','+91-7541896320','India','24AABCJ2345Z1Z1','jai.plastics@gmail.com','Loc',0,'2024-08-12'),
(14,'Sivay Textiles','Ichalkaranji, Maharashtra - 416115','+91-7485963210','India','27AABCS8901A1Z4','sivay.textiles@yahoo.in','IGST',0,'2024-09-07'),
(15,'Dro Chemicals','Ankleshwar GIDC, Gujarat - 393002','+91-7894561230','India','24AABCD4567B1Z9','dro.chem@gmail.com','Loc',0,'2024-10-22'),
(16,'Sibvkj Agro','Rajkot, Gujarat - 360004','+91-7894561230','India','24AABCS0123C1Z3','sibvkj.agro@gmail.com','Loc',0,'2024-11-05'),
(17,'Retuy Pharma','Vatva GIDC, Ahmedabad - 382445','+91-8735003590','India','24AABCR5678D1Z7','retuy.pharma@gmail.com','Loc',0,'2024-12-01'),
(18,'We Ho Foods','Surat, Gujarat - 395003','+91-8735003590','India','24AABCW9012E1Z5','weho.foods@gmail.com','Loc',0,'2025-01-05'),
(19,'Slope Engineering','Vadodara, Gujarat - 390010','+91-7894561230','India','24AABCS3456F1Z8','slope.engg@gmail.com','Loc',0,'2025-01-10'),
(20,'Zecome Industries','Vapi GIDC, Gujarat - 396195','+91-7600158240','India','24AABCZ7890G1Z2','zecome.ind@gmail.com','Loc',0,'2025-01-14'),
(21,'Sunita Rubber Works','Sion, Mumbai - 400022','+91-9820087623','India','27AABCS1234H1Z6','sales@sunitarubber.in','IGST',1,'2023-06-20'),
(22,'Delta Automation','Andheri East, Mumbai - 400069','+91-9820098234','India','27AABCD5678I1Z1','info@deltaautomation.in','IGST',1,'2023-07-15'),
(23,'HP Ink Solutions','Nariman Point, Mumbai - 400021','+91-9820012345','India','27AABCH9012J1Z9','sales@hpinksolutions.com','IGST',1,'2023-08-25'),
(24,'Multispan Instruments','Sarkhej, Ahmedabad - 382210','+91-7600167890','India','24AABCM3456K1Z3','sales@multispan.co.in','Loc',1,'2023-09-30'),
(25,'Gujarat Belting Co','Odhav, Ahmedabad - 382415','+91-7600178901','India','24AABCG7890L1Z7','info@gujaratbelting.in','Loc',1,'2023-10-12'),
(26,'Krishna Packaging','Bhiwandi, Maharashtra - 421302','+91-9820034567','India','27AABCK2345M1Z5','krishna.pack@gmail.com','IGST',2,'2023-11-08'),
(27,'Aditya Enterprises','Nashik, Maharashtra - 422007','+91-9820045678','India','27AABCA6789N1Z2','aditya.ent@gmail.com','IGST',2,'2024-01-20'),
(28,'Mahaveer Transport','Kalamboli, Navi Mumbai - 410218','+91-9870056789','India','27AABCM1234O1Z8','mahaveer.trans@gmail.com','IGST',2,'2024-03-14'),
(29,'Trupti Plastics','Rajkot, Gujarat - 360004','+91-7485963210','India','24AABCT5678P1Z4','trupti.plastics@gmail.com','Loc',2,'2024-05-25'),
(30,'Nirav Chemicals','Ankleshwar, Gujarat - 393002','+91-7894561230','India','24AABCN9012Q1Z1','nirav.chem@gmail.com','Loc',2,'2024-07-19'),
(31,'Bhavya Engineers','Vatva, Ahmedabad - 382445','+91-8735003590','India','24AABCB3456R1Z9','bhavya.engg@gmail.com','Loc',2,'2024-09-11'),
(32,'Dhruv Industrial','Surat, Gujarat - 395003','+91-7600158240','India','24AABCD7890S1Z3','dhruv.ind@gmail.com','Loc',2,'2024-11-28'),
(33,'Riddhi Traders','Vadodara, Gujarat - 390010','+91-7894561230','India','24AABCR1234T1Z7','riddhi.traders@gmail.com','Loc',2,'2025-01-12');

-- =====================================================================
-- ACCOUNTS
-- =====================================================================

CREATE TABLE "account" (
  "aid"         INTEGER PRIMARY KEY AUTOINCREMENT,
  "cid"         INTEGER NOT NULL,
  "acc_type"    INTEGER NOT NULL,
  "opening_bal" REAL NOT NULL,
  "created"     TEXT NOT NULL
);
INSERT INTO "account" VALUES
(1,1,0,201723,'2023-08-11'),
(2,2,0,45000,'2023-09-05'),
(3,3,0,125000,'2023-10-18'),
(4,4,0,0,'2023-11-02'),
(5,5,0,78500,'2023-12-14'),
(6,6,0,15000,'2024-01-08'),
(7,7,0,0,'2024-02-15'),
(8,8,0,92000,'2024-03-20'),
(9,9,0,0,'2024-04-11'),
(10,10,0,34000,'2024-05-06'),
(11,11,0,0,'2024-06-19'),
(12,12,0,10000,'2024-07-03'),
(13,13,0,0,'2024-08-12'),
(14,14,0,56000,'2024-09-07'),
(15,15,0,0,'2024-10-22'),
(16,16,0,23000,'2024-11-05'),
(17,17,0,0,'2024-12-01'),
(18,18,0,0,'2025-01-05'),
(19,19,0,0,'2025-01-10'),
(20,20,0,0,'2025-01-14'),
(21,21,1,0,'2023-06-20'),
(22,22,1,0,'2023-07-15'),
(23,23,1,0,'2023-08-25'),
(24,24,1,0,'2023-09-30'),
(25,25,1,0,'2023-10-12'),
(26,26,2,0,'2023-11-08'),
(27,27,2,0,'2024-01-20'),
(28,28,2,0,'2024-03-14'),
(29,29,2,0,'2024-05-25'),
(30,30,2,0,'2024-07-19'),
(31,31,2,0,'2024-09-11'),
(32,32,2,0,'2024-11-28'),
(33,33,2,0,'2025-01-12');

-- =====================================================================
-- DELIVERY ADDRESSES
-- =====================================================================

CREATE TABLE "delivery_addresses" (
  "delid"   INTEGER PRIMARY KEY AUTOINCREMENT,
  "invid"   TEXT NOT NULL,
  "name"    TEXT NOT NULL,
  "address" TEXT NOT NULL,
  "mob"     TEXT NOT NULL
);
INSERT INTO "delivery_addresses" ("invid","name","address","mob") VALUES
('INV/24-25/0002','Gamer Packaging - Warehouse','Plot 45, MIDC Andheri East, Mumbai - 400093','+91-9820033591'),
('INV/24-25/0003','Diamond Foods - Plant 2','Peenya Industrial Area, Phase 2, Bengaluru - 560058','+91-9880016240'),
('INV/24-25/0005','Cyan Pharma - Unit 3','Lower Parel, Mumbai - 400013','+91-9820046240'),
('INV/24-25/0007','Simon Traders - Godown','Nehru Place, New Delhi - 110019','+91-9810016240'),
('INV/24-25/0008','Amplify Beverages - Factory','HSR Layout, Sector 2, Bengaluru - 560102','+91-9880061230');

-- =====================================================================
-- FIXED DEPOSITS
-- =====================================================================

CREATE TABLE "fd" (
  "id"            INTEGER PRIMARY KEY AUTOINCREMENT,
  "fdissueddate"  TEXT,
  "fdholder"      TEXT NOT NULL,
  "fdofbank"      TEXT NOT NULL,
  "principleamt"  INTEGER NOT NULL,
  "nodays"        TEXT NOT NULL,
  "intrate"       TEXT NOT NULL,
  "intamt"        INTEGER NOT NULL,
  "finalamt"      INTEGER NOT NULL,
  "maturitydate"  TEXT NOT NULL,
  "fdentrydate"   TEXT NOT NULL
);
INSERT INTO "fd" VALUES
(1,'2024-03-02','Tejas Chavda','Saraswat Cooperative Bank',500000,'365','7.25',36250,536250,'2025-03-02','2024-03-02 10:30:00'),
(2,'2024-06-15','CodeTech Engineers','ICICI Bank',1000000,'180','6.50',32500,1032500,'2024-12-12','2024-06-15 14:20:00'),
(3,'2024-09-01','Tejas Chavda','HDFC Bank',250000,'90','5.75',3594,253594,'2024-11-30','2024-09-01 09:45:00'),
(4,'2025-01-01','CodeTech Engineers','SBI',750000,'365','7.00',52500,802500,'2026-01-01','2025-01-01 11:00:00');

-- =====================================================================
-- FESTIVALS
-- =====================================================================

CREATE TABLE "fest" (
  "id"         INTEGER PRIMARY KEY AUTOINCREMENT,
  "date"       TEXT NOT NULL,
  "fest_name"  TEXT NOT NULL,
  "gifs"       TEXT NOT NULL
);
INSERT INTO "fest" ("date","fest_name","gifs") VALUES
('14-Jan','Uttarayan / Makar Sankranti','kite-festival.gif'),
('26-Jan','Republic Day','republic-day.gif'),
('18-Feb','Maha Shivaratri','mahashivratri.gif'),
('25-Mar','Holi','happy-holi.gif'),
('15-Aug','Independence Day','independence-day.gif'),
('02-Oct','Gandhi Jayanti','gandhi-jayanti.gif'),
('20-Oct','Diwali','happy-diwali.gif'),
('25-Dec','Christmas','merry-christmas.gif');

-- =====================================================================
-- SALES INVOICES
-- =====================================================================

CREATE TABLE "invtest" (
  "orderno"    INTEGER PRIMARY KEY AUTOINCREMENT,
  "orderid"    TEXT NOT NULL,
  "item_name"  TEXT NOT NULL,
  "item_desc"  TEXT,
  "hsn"        INTEGER NOT NULL,
  "quantity"   INTEGER NOT NULL,
  "price"      INTEGER NOT NULL,
  "total"      INTEGER NOT NULL
);
INSERT INTO "invtest" ("orderid","item_name","item_desc","hsn","quantity","price","total") VALUES
('677eb6940aac8','CT-01 HandHeld Manual Coder','Font Kit 2.5 mm',8443,1,4000,4000),
('677eb6940aac8','Inkpad Holder','Black plastic form pad holder',8443,2,1500,3000),
('677eb6b93db03','CT-02 Handy Marker for Corrugated Cartons','Font kit 10 mm',8443,1,8500,8500),
('677f49a69a9cb','CT-05 Table Top Coder','Complete set with accessories',8443,1,45000,45000),
('67874b54c5345','CT-01 HandHeld Manual Coder','Font Kit 2.5 mm',8443,3,3500,10500),
('67874b54c5345','Font Kit 3 mm','Normal by Sunita',8443,4,500,2000),
('67874ba2f24b5','CT-07 Standard Multipurpose Coder','Wooden Packing',8443,1,85000,85000),
('67874ba2f24b5','Paste Ink','Paste Ink 1L',8443,5,2000,10000),
('67874c1a1b2c3','CT-03 Handy Marker for HDPE Bags','Font kit 12mm',8443,1,5500,5500),
('67874d2b2c3d4','Standard Label Coder','Label Coder',8443,1,30000,30000),
('67874d2b2c3d4','H.P Cartridge','47 ml Ink Cartridge',8443,1,5000,5000),
('67874e3c3d4e5','CT-07 Ice Cream Multipurpose Coder','Includes Wooden Packing',8443,1,65000,65000);

CREATE TABLE "invtest2" (
  "invid"       TEXT PRIMARY KEY,
  "cid"         INTEGER NOT NULL,
  "orderid"     TEXT NOT NULL,
  "totalitems"  INTEGER NOT NULL,
  "subtotal"    INTEGER NOT NULL,
  "taxrate"     INTEGER NOT NULL,
  "taxamount"   INTEGER NOT NULL,
  "totalamount" INTEGER NOT NULL,
  "created"     TEXT NOT NULL
);
INSERT INTO "invtest2" VALUES
('INV/24-25/0001',1,'677eb6940aac8',2,7000,18,1260,8260,'2024-04-15'),
('INV/24-25/0002',2,'677eb6b93db03',1,8500,18,1530,10030,'2024-05-22'),
('INV/24-25/0003',3,'677f49a69a9cb',1,45000,18,8100,53100,'2024-06-10'),
('INV/24-25/0004',4,'67874b54c5345',3,12500,18,2250,14750,'2024-08-18'),
('INV/24-25/0005',5,'67874ba2f24b5',2,95000,18,17100,112100,'2024-10-05'),
('INV/24-25/0006',6,'67874c1a1b2c3',1,5500,18,990,6490,'2024-11-20'),
('INV/24-25/0007',7,'67874d2b2c3d4',2,35000,18,6300,41300,'2024-12-15'),
('INV/24-25/0008',8,'67874e3c3d4e5',1,65000,18,11700,76700,'2025-01-08');

-- =====================================================================
-- PAYMENTS
-- =====================================================================

CREATE TABLE "paidhistory" (
  "pay_id"          TEXT PRIMARY KEY,
  "cid"             TEXT NOT NULL,
  "amount"          INTEGER NOT NULL,
  "bank"            TEXT NOT NULL,
  "dateofpayment"   TEXT NOT NULL,
  "purpose"         TEXT NOT NULL,
  "created"         TEXT NOT NULL
);
INSERT INTO "paidhistory" VALUES
('RCP/24-25/0001','1',200000,'ICICI BANK','2024-04-20','Against INV/24-25/0001 - Full settlement','2024-04-20 11:30:00'),
('RCP/24-25/0002','2',10030,'HDFC BANK','2024-05-28','Against INV/24-25/0002 - NEFT','2024-05-28 15:45:00'),
('RCP/24-25/0003','3',53100,'ICICI BANK','2024-06-18','Against INV/24-25/0003 - RTGS','2024-06-18 10:20:00'),
('RCP/24-25/0004','4',14750,'SBI','2024-08-25','Against INV/24-25/0004 - UPI','2024-08-25 17:10:00'),
('RCP/24-25/0005','5',50000,'ICICI BANK','2024-10-12','Part payment against INV/24-25/0005','2024-10-12 12:00:00'),
('RCP/24-25/0006','5',62100,'ICICI BANK','2024-11-02','Balance against INV/24-25/0005','2024-11-02 14:30:00'),
('RCP/24-25/0007','6',6490,'ICICI BANK','2024-11-25','Against INV/24-25/0006 - Cash','2024-11-25 16:00:00'),
('RCP/24-25/0008','7',41300,'HDFC BANK','2024-12-22','Against INV/24-25/0007 - NEFT','2024-12-22 11:15:00'),
('RCP/24-25/0009','8',76700,'ICICI BANK','2025-01-12','Against INV/24-25/0008 - RTGS','2025-01-12 09:45:00');

-- =====================================================================
-- PRODUCTS  (now with cattype column)
-- =====================================================================

CREATE TABLE "products" (
  "p_id"        INTEGER PRIMARY KEY AUTOINCREMENT,
  "name"        TEXT NOT NULL,
  "hsn"         INTEGER NOT NULL,
  "description" TEXT NOT NULL,
  "p_type"      TEXT NOT NULL,
  "cattype"     TEXT NOT NULL DEFAULT 'General',
  "img_loc"     TEXT,
  "techs"       TEXT,
  "created"     TEXT NOT NULL
);

INSERT INTO "products" ("p_id","name","hsn","description","p_type","cattype","img_loc","techs","created") VALUES
(1,'CT- 01 HandHeld Manual Coder',8443,'Font Kit 2.5 mm','Machine','Machine','hand stamp.jpg','Printing Area : 35 x 60 mm (LxB);Prints using Grooves Rubber based stereo (3  MM); Ink- Fast dry & Water Resistant; Weight 0.5 kgs; Comes with 500ml ink, 500ml Cleaner, Groove fonts & Inkpad (2pcs)','2020-07-02'),
(2,'CT- 02 Handy Marker for Currogated Cartons',8443,'Font kit 10 mm','Machine','Machine','handy box.jpg','Printing Area : 3x12 inch (LxB);Prints using Grooves Rubber based stereo (12  MM); Ink Roller – Rechargeable high capacity porous ink;Impression -  1,000 per charge of 20ml / 40ml. /10 ml(depending upon no. of lines printed);Weight - 3kgs;Comes with 1 liter porus ink.','2022-02-26'),
(3,'CT-03 Handy Marker for HDPE Bags',8443,'Font kit 12mm','Machine','Machine','handy bag.jpg','Printing Area : 3x12 inch (LxB);Prints using Grooves Rubber based stereo (12  MM);Ink Roller – Rechargeable high capacity non porous ink;Impression -  1,000 per charge of 20ml / 40ml. /10 ml. (depending upon no. of lines printed);Weight - 3kgs;Comes with 1 liter HDPE ink, 1 Liter ink-aid & Tools.','2022-02-26'),
(4,'CT-05 Table Top Coder ',8443,'Complete set','Machine','Machine','table top.jpg','Printing Area – 35 x 35 mm (LxB);Operating Method – Foot Switch & Continuous Both.;Power – 230 V AC 50 Hz;Print material: rubber stereo 3 mm sheet.;Comes with -  PLC motor, Liquid Fast dry Ink(500 ml),ink Roll, Form Pad, Tools, Circuit Board controller, Cleaner(500 ml).; Printing Speed (Max) - 60 Nos/Min.;Comes with Complete protective box','2020-12-16'),
(5,'CT-07 Standard Multipurpose Coder',8443,'Wooden Packing','Machine','Machine','2in1.jpg','Overall Dimensions: 1070 x 680 x 450;Speed: 150 cartons/min.  250 labels/min.;Pouch/Carton Size: 80mm x 40mm to 305mm x 200mm;Power : 0.5HP  3 phase;Weight: Approx. 100 Kgs;Prints using Rubber Stereo.;Materials along with m/c: 500ml paste Ink, tape roll,Tools.','2020-12-21'),
(6,'CT-07 Ice Cream Multipurpose Coder',8443,'Includes Wooden Packing','Machine','Machine','2in1.jpg','Overall Dimensions: 1070 x 680 x 450;Speed: 150 cartons/min.  250 labels/min.;Pouch/Carton Size: 80mm x 40mm to 305mm x 200mm;Power : 0.5HP  3 phase;Weight: Approx. 100 Kgs;Prints using Rubber Stereo.;Materials along with m/c: 500ml paste Ink, tape roll,Tools.','2020-12-21'),
(7,'2in1 coder',8443,'includes wooden packing','Machine','Machine','2in1.jpg','Overall Dimensions: 1070 x 680 x 450;Speed: 150 cartons/min.  250 labels/min.;Pouch/Carton Size: 80mm x 40mm to 305mm x 200mm;Power : 0.5HP  3 phase;Weight: Approx. 100 Kgs;Prints using Rubber Stereo.;Materials along with m/c: 500ml paste Ink, tape roll,Tools.','2020-05-05'),
(8,'Standard Carton Coder',8443,'With Counting Sensor and Delta','Machine','Machine','standard carton.jpg','Overall Dimensions: 1010 x 690 x 590;Speed:   250 cartons/min.;Carton Size: 80mm x 25mm to 305mm x 200mm;Power : 0.5HP  3 phase;Weight: Approx. 102 Kgs;Prints using Rubber Stereo.;Materials along m/c:  500ml paste Ink, tape roll,Liquid block, Tools & Liquid ink.','2020-05-14'),
(14,'Inkpad',8443,'white font pad','Consumables','Consumables','','','2020-06-04'),
(15,'Inkpad Holder',8443,'Black plastic form pad holder ','Consumables','Consumables','','','2024-10-12'),
(17,'High Speed Carton Stracker',8443,'Standard','Machine','Machine','','','2020-06-07'),
(18,'SpgInk',8443,'Antifreeze','Consumables','Consumables','','','2020-06-08'),
(19,'C - Feeding Rubber',8443,'Carton Feeding Rubber ','Consumables','Consumables','','','2020-06-08'),
(20,'L - Feeding Rubber',8443,'Label Feeding Rubber','Consumables','Consumables','','','2020-06-08'),
(21,'Paste Ink',8443,'Paste Ink','Consumables','Consumables','','','2020-06-08'),
(25,'Black Rubber strip Plain',8443,'Rubber strip','Consumables','Consumables','','','2020-06-10'),
(26,'Anti-Freeze Fast Dry Ink',8443,'antifreeze','Consumables','Consumables','','','2020-06-19'),
(27,'Font Kit 3 mm',8443,'Normal by sunita','Consumables','Consumables','','','2020-06-26'),
(28,'Font Kit 4 mm',8443,'font kit orange ','Consumables','Consumables','','','2020-06-26'),
(29,'Groove Sheet',8443,'Black ','Consumables','Consumables','1736181106_299dea25c8011296392b.jpg','','2025-01-06'),
(31,'Courier',8443,'trackon, mahaveer','Freight','Freight','courier.png','','2020-07-05'),
(32,'Wooden Packing',4416,'wooden','Freight','Freight','','','2025-02-04'),
(33,'Freight Charges',8443,'freight','Freight','Freight','logistic.png','','2020-09-07'),
(34,'Mini High Speed Inkjet Stacker ',8443,'ade','Machine','Machine','','','2023-07-25'),
(36,'Font Kit 2mm',8443,'sd','Consumables','Consumables','','','2020-06-11'),
(37,'Ink Roll',8443,'hjk','Consumables','Consumables','','','2020-07-21'),
(38,'Porous Ink Roll',8443,'645654','Consumables','Consumables','','','2020-07-20'),
(39,'Spring',8443,'5654','Consumables','Consumables','','','2020-07-20'),
(40,'TUFT Pink Belt For High Speed Stracker',8443,'dfgdrh','Consumables','Consumables','','','2020-07-22'),
(41,'Grooved Logo Sheet',8443,'ytrhrth','Consumables','Consumables','','','2020-07-28'),
(42,'Ink-Aid',8443,'INK AID','Consumables','Consumables','','','2020-08-24'),
(43,'Standard Label Coder',8443,'Label Coder','Machine','Machine','standard label.jpg','Overall Dimensions: 880 x 530 x 460;Speed:  250 labels/min.;Label Size: 20mm x 40mm to 150mm x 200mm;Power: 0.5HP  3 phase;Weight: Approx. 80 Kgs;Prints using Rubber Stereo.;Materials along with machine: Paste ink, 2 sided tape,Tools & Feeding Rubber ','2020-09-03'),
(44,'High Speed Pouch Inkjet Stracker ',8443,'adsjdsahsdkjh','Machine','Machine','','','2020-09-07'),
(45,'Font Kit 12 mm',8443,'kjdfhkjshkl','Consumables','Consumables','','','2020-09-14'),
(46,'Logo Sheet',8443,'jsdhkjsah','Consumables','Consumables','','','2020-09-14'),
(47,'CT - 14 High Speed Inkjet Stracker',8443,'sjhsak','Machine','Machine','','','2020-10-05'),
(48,'Font Kit 25mm',8443,'therhgrth','Consumables','Consumables','','','2020-10-20'),
(49,'Code Equipment',8443,'ddfus','Consumables','Consumables','','','2020-10-23'),
(50,'Font kit 10 mm',8443,'jdsnkjd','Consumables','Consumables','','','2020-10-24'),
(51,'Font kit 6mm',8443,'defewf','Consumables','Consumables','','','2020-10-29'),
(52,'Font kit 14 mm',8443,'kljlkj','Consumables','Consumables','','','2020-12-14'),
(53,'Handy Marker for Jute Bags',8443,'8232','Machine','Machine','','','2020-12-14'),
(54,'Ice Cream 2in1 Coder',8443,'hgsdajhg','Machine','Machine','','','2021-01-11'),
(55,'Packing and forwarding',8443,'ewe','Freight','Freight','','','2021-02-06'),
(56,'Stereo Sheet 2mm',8443,'thtrfh','Consumables','Consumables','','','2021-03-06'),
(57,'Stereo Sheet 3mm',8443,'fdgdtrh','Consumables','Consumables','','','2021-03-06'),
(58,'2in Gear 7.5 inch dia',8443,'l[ihwieoiqh','Consumables','Consumables','','','2021-03-12'),
(59,'Feeding Rubber',8443,'hdjkshk','Consumables','Consumables','','','2021-03-15'),
(61,'HDPE Bag Ink',8443,'fdkljhf','Consumables','Consumables','','','2020-05-28'),
(62,'Plain Pad',8443,'dsjsk','Consumables','Consumables','','','2021-04-06'),
(63,'2 Sided Tape ',8443,'dsidsji','Consumables','Consumables','','','2021-04-06'),
(64,'Box Ink',8443,'jytj','Consumables','Consumables','','','2021-04-07'),
(65,'Font kit 8 mm',8443,'21445','Consumables','Consumables','','','2021-04-10'),
(66,'Delta VFD Drive + Multispan Counter',8443,'dslihwejkh','Consumables','Consumables','','','2021-04-13'),
(67,'Hand Printer',84229090,'jkbiuljk','Machine','Machine','','','2021-05-28'),
(68,'High Speed Multipurpose Inkjet Stracker',8443,'dsljgfdjgb','Machine','Machine','','','2021-06-04'),
(69,'Pusher Assembly',8443,'edwejklujtgewuyy','Consumables','Consumables','','','2021-06-04'),
(70,'NP Ink Roll',8443,'uktu','Consumables','Consumables','','','2021-06-09'),
(71,'Handy Coder for Plywood',8443,'dsf.,khsdk','Machine','Machine','','','2021-06-10'),
(72,'Handy Marker for HDPE Bags',8443,'trete','Machine','Machine','','','2021-06-14'),
(73,'Font kit 20 mm',8443,'efe','Consumables','Consumables','','','2021-06-15'),
(74,'Font kit 25 mm',8443,'ettewe','Consumables','Consumables','','','2021-06-25'),
(75,'H.P Cartridge',8443,'4564534','Consumables','Consumables','hp cartridge.jpg','47 ml Ink Cartridge;No chip Cartridge;HP Original Seal Pack Cartridge;Print Head 12.7mm;Solvent Ink;Fast Dry & Permanent ','2021-06-26'),
(76,'Handheld Inkjet Printer JD-007',8443,'kuhdfwkjjhk','Machine','Machine','','','2021-09-30'),
(77,'Wiper',8443,'adsskihdwoih','Consumables','Consumables','','','2021-07-12'),
(78,'Thermal Inkjet Printer  -  T180',8443,'dfgdfsd','Machine','Machine','m 302.jpg','Max.Print Height : 12.7 mm;Max. Speed : 80-200 per...','2021-07-30'),
(79,'High Speed Medical Cassete Feeder ',8443,'chsdkjdh','Machine','Machine','','','2021-08-23'),
(80,'Black Plain PVC Belt',8443,'44444','Consumables','Consumables','','','2021-08-31'),
(81,'Electromechanical Coder',8443,'dfuugsidugg','Machine','Machine','','','2021-09-22'),
(82,'Metal Sensor for inkjet',8443,'jjdsggjuhjsdg','Consumables','Consumables','','','2021-09-24'),
(83,'Gearbox Varam wheel with shaft',8443,'jsdajhkjsaha','Consumables','Consumables','','','2021-09-28'),
(84,'Shaft Roller for Feeding Conevyor',8443,'kdsjgsdjg','Consumables','Consumables','','','2021-09-30'),
(85,'High Speed Label Inkjet Feeder',8443,'jsdgjug','Machine','Machine','','','2021-10-09'),
(86,'Blue cartridge',8443,'gdsajhg','Consumables','Consumables','','','2021-10-13'),
(87,'Handheld Inkjet Printer JJ-007',8443,'jsdguy','Machine','Machine','','','2021-10-16'),
(88,'H.P Solvent Cartridge',8443,'hgk','Consumables','Consumables','hp cartridge.jpg','47 ml Ink Cartridge;No chip Cartridge;HP Original Seal Pack Cartridge;Print Head 12.7mm;Solvent Ink;Fast Dry & Permanent ','2021-10-21'),
(89,'HP Water Based Cartridge',8443,'hgfh','Consumables','Consumables','','','2021-10-21'),
(91,'Battery',8443,'gnny','Consumables','Consumables','','','2021-10-23'),
(92,'Handy Coder for Metallic Surface',8443,'kjhsdiks','Machine','Machine','','','2021-10-25'),
(93,'Handy coder',8443,'kjjhdfkjh','Machine','Machine','','','2021-11-10'),
(94,'Handheld Inkjet printer - KGP 001',8443,'dhwjshvjhv','Machine','Machine','','','2021-11-22'),
(95,'Semi-Automatic Sticker Labeling',8422,'jhdsafuyf','Machine','Machine','','','2021-11-26'),
(96,'Extra Modification',8422,'isdjikk','Consumables','Consumables','','','2021-11-26'),
(97,'Handheld Inkjet Printer - KG 001',8443,'jhjfdsiug','Machine','Machine','','','2021-11-26'),
(98,'Double bond cartridge',8443,'dfksuhukj','Consumables','Consumables','double bond.jpg','Japanese Cartridge;High cohesion on Glossy Surface...','2021-12-01'),
(99,'Motor Belt',8443,'kugsdfiu','Consumables','Consumables','','','2021-12-25'),
(100,'Simple Conveyor',8443,'767665','Machine','Machine','simple conveyor.jpeg','Machine Length - 1500 mm; Machine Width -  350 mm;...','2021-12-27'),
(101,'Feeding Belt',8443,'dshkj','Consumables','Consumables','','','2021-12-31'),
(102,'White roller with Oring',8443,'hdsjkgh','Consumables','Consumables','','','2021-12-31'),
(103,'Center Roller ',8443,'jdfsikj','Consumables','Consumables','','','2021-12-31'),
(104,'Encoder Wheel + Bracket',8443,'dsihjikjh','Consumables','Consumables','','','2021-12-31'),
(105,'T-180 Inkjet Printer',8443,'dsihjikjh','Machine','Machine','','','2022-01-03'),
(106,'White Cartridge',8443,'jkbjhv','Consumables','Consumables','','','2022-01-06'),
(107,'Handy Stand Assembly',8443,'bdfjeh','Consumables','Consumables','','','2022-01-10'),
(109,'codpad printer',8443,'kdushkfjd','Machine','Machine','','','2022-01-14'),
(111,'Empty Bottle',8443,'kusdfgiuds','Consumables','Consumables','','','2022-01-17'),
(112,'Encoder ',8443,'yryuy','Consumables','Consumables','','','2022-01-20'),
(114,'Long Rubber -CL',8443,'geskj','Consumables','Consumables','','','2022-02-01'),
(115,'Motor with Gearbox ',8443,'ytyt','Consumables','Consumables','','','2022-02-05'),
(116,'Gearbox ',8443,'isoi','Consumables','Consumables','','','2022-02-05'),
(117,'Duplex Gear',8443,'kd','Consumables','Consumables','','','2019-12-19'),
(118,'Bronze Bush',8443,'jgsd','Consumables','Consumables','','','2019-12-19'),
(119,'Reling Rubber',8443,'jsjhgj','Consumables','Consumables','','','2019-12-19'),
(120,'Bosh Gear',8443,'kkshiu','Consumables','Consumables','','','2019-12-19'),
(121,'Nut Bolt',8443,'jgsj','Consumables','Consumables','','','2020-02-24'),
(122,'object Sensor for Inkjet',8443,'4555','Consumables','Consumables','','','2022-03-21'),
(123,'Solvent Ink Cartridge',8443,'jyj','Consumables','Consumables','','','2022-03-21'),
(124,'Thermal  Inkjet Printer - M302 ',8443,'fdghrdh','Machine','Machine','','','2022-04-11'),
(125,'Repairing',8443,'yfyujyuj','Consumables','Consumables','','','2022-04-30'),
(126,'Delta VFD Drive',8443,'sjdlkj','Consumables','Consumables','','','2022-05-25'),
(127,'Green Cartridge',8443,'jbnj','Consumables','Consumables','','','2022-06-04'),
(128,'Green Carton Special Belt',8443,'jhsdkjhsdkj','Consumables','Consumables','','','2022-09-11'),
(129,'CT-03 Touch Screen Coder',8443,'rgdfg','Machine','Machine','','','2022-11-07'),
(130,'Touch Screen Coder',8443,'ihuhiu','Machine','Machine','','','2022-11-12'),
(131,'Mini Printer',8443,'esfew','Machine','Machine','mini printer.jpg','Max.Print Height : 12.7 mm;Max. Speed : 30-40 per/min.;LCD  Display;Comes along pen drive , HP original Seal Pack Black ink Cartridge , charger;NO Courier Charges','2022-11-15'),
(132,'Porous Spgink',8443,'hsg','Consumables','Consumables','','','2022-12-02'),
(133,'Water Based Black Porous Ink',8443,'sdjgjh','Consumables','Consumables','','','2022-12-02'),
(134,'Screw',8443,'lidf','Consumables','Consumables','','','2022-12-27'),
(135,'Auto-Collector Conveyor',8443,'sdfdsdd','Machine','Machine','','','2023-01-31'),
(136,'CT - 13 Thermal Inkjet Printer ',8443,'kreuuijk','Machine','Machine','','','2023-03-02'),
(137,'Manual Induction',8443,'fdsfd','Machine','Machine','','','2023-03-18'),
(138,'Stand Bracket with sensor',8443,'iuoio','Consumables','Consumables','','','2023-03-27'),
(139,'Bandsealer',8443,'hfhg','Machine','Machine','','','2023-04-21'),
(140,'weigh filler',8443,'uyuy','Machine','Machine','','','2023-04-21'),
(141,'Printer Cartridge',8443,'jhhk','Consumables','Consumables','','','2023-05-15'),
(142,'Charger',8443,'hsdkh','Consumables','Consumables','','','2023-06-30'),
(143,'Stereo',8443,'ghhfdd','Consumables','Consumables','','','2023-07-11'),
(145,'stamp handle',8443,'dsfrdsfe','Consumables','Consumables','','','2023-09-29'),
(146,'Yellow Cartridge',8443,'jhkj','Consumables','Consumables','','','2023-10-11'),
(147,'Display',8443,'Display','Machine','Machine','','','2023-10-16'),
(148,'Pressure Roller for stracker',8443,'dfedfer','Consumables','Consumables','','','2023-11-30'),
(149,'Print Driver Board',8443,'sdfhfsdkjhfi','Consumables','Consumables','','','2023-12-07'),
(150,'Cable Strip',8443,',dsjhfdkjsh','Consumables','Consumables','','','2023-12-06'),
(151,'Orings ',8443,'jkhsdkjhdskj','Consumables','Consumables','','','2023-12-07'),
(152,'touch pen',8443,'klsdfjflkdsj','Consumables','Consumables','','','2023-12-07'),
(154,'cartridge inserting plastic block',8443,'jksdhdjskh','Consumables','Consumables','','','2024-01-11'),
(155,'Locking Stip Latch',8443,'dkjhkjh','Consumables','Consumables','','','2024-04-10'),
(156,'Stand Assembly',8443,'wsjkeykj','Consumables','Consumables','','','2024-04-17'),
(157,'Q Shape Plastic',8443,'56u','Consumables','Consumables','','','2024-05-18'),
(158,'CMos Battery Cell',8443,'jhgejeg','Consumables','Consumables','','','2024-05-23'),
(159,'Touch Screen',8443,'dtgertr','Consumables','Consumables','','','2024-06-14'),
(160,' Assembly for Auto-collector',8443,'fdkfjgkuew','Consumables','Consumables','','','2024-09-20'),
(161,'Porter Delivery',8443,'sutgduig ','Freight','Freight','','','2024-09-21'),
(165,'flow ',8443,'jwe w','Consumables','Consumables','1736942221_14cd51e0eb5d58f3b95a.jpg','Printing Area : 35 x 60 mm (LxB);Prints using Grooves Rubber based stereo (3  MM); Ink- Fast dry & Water Resistant; Weight 0.5 kgs; Comes with 500ml ink, 500ml Cleaner, Groove fonts & Inkpad (2pcs)','2025-01-15');

-- =====================================================================
-- PROFORMA INVOICES
-- =====================================================================

CREATE TABLE "protest" (
  "orderno"    INTEGER PRIMARY KEY AUTOINCREMENT,
  "orderid"    TEXT NOT NULL,
  "item_name"  TEXT NOT NULL,
  "item_desc"  TEXT,
  "hsn"        INTEGER NOT NULL,
  "quantity"   INTEGER NOT NULL,
  "price"      INTEGER NOT NULL,
  "total"      INTEGER NOT NULL
);
INSERT INTO "protest" ("orderid","item_name","item_desc","hsn","quantity","price","total") VALUES
('677eb8aff273c','CT-01 HandHeld Manual Coder',NULL,8443,1,5000,5000),
('677f497c81839','CT-02 Handy Marker for Currogated Cartons',NULL,8443,1,4000,4000),
('677f7a4bbdd86','CT-05 Table Top Coder',NULL,8443,1,30000,30000),
('677f7a5d289b4','Font Kit 3 mm',NULL,8443,1,500,500),
('677f7a7272192','Inkpad Holder',NULL,8443,1,50,50),
('677f7a97dba57','2in1 coder',NULL,8443,1,50000,50000),
('677f7aaae39a5','CT-05 Table Top Coder',NULL,8443,1,35000,35000),
('678747a3b1ea1','CT-01 HandHeld Manual Coder',NULL,8443,1,3000,3000),
('67874af9f182a','CT-02 Handy Marker for Currogated Cartons',NULL,8443,1,4000,4000);

CREATE TABLE "protest2" (
  "invid"       TEXT PRIMARY KEY,
  "cid"         INTEGER NOT NULL,
  "orderid"     TEXT NOT NULL,
  "totalitems"  INTEGER NOT NULL,
  "subtotal"    INTEGER NOT NULL,
  "taxrate"     INTEGER NOT NULL,
  "taxamount"   INTEGER NOT NULL,
  "totalamount" INTEGER NOT NULL,
  "created"     TEXT NOT NULL
);
INSERT INTO "protest2" VALUES
('PI/24-25/0001',1,'677eb8aff273c',1,5000,18,900,5900,'2024-02-15'),
('PI/24-25/0002',4,'677f497c81839',1,4000,18,720,4720,'2024-04-20'),
('PI/24-25/0003',7,'677f7a4bbdd86',1,30000,18,5400,35400,'2024-07-10'),
('PI/24-25/0004',7,'677f7a5d289b4',1,500,18,90,590,'2024-07-10'),
('PI/24-25/0005',6,'677f7a7272192',1,50,18,9,59,'2024-08-05'),
('PI/24-25/0006',4,'677f7a97dba57',1,50000,18,9000,59000,'2024-09-12'),
('PI/24-25/0007',7,'677f7aaae39a5',1,35000,18,6300,41300,'2024-10-22'),
('PI/24-25/0008',6,'678747a3b1ea1',1,3000,18,540,3540,'2024-12-18'),
('PI/24-25/0009',1,'67874af9f182a',1,4000,18,720,4720,'2025-01-08');

-- =====================================================================
-- PURCHASE INVOICES
-- =====================================================================

CREATE TABLE "purchaseinv" (
  "orderno"    INTEGER PRIMARY KEY AUTOINCREMENT,
  "orderid"    TEXT NOT NULL,
  "item_name"  TEXT NOT NULL,
  "item_desc"  TEXT,
  "hsn"        INTEGER NOT NULL,
  "quantity"   INTEGER NOT NULL,
  "price"      INTEGER NOT NULL,
  "total"      INTEGER NOT NULL
);
INSERT INTO "purchaseinv" ("orderid","item_name","item_desc","hsn","quantity","price","total") VALUES
('677eb7ba2e3c8','Grooved Rubber Sheet','3mm thickness',4008,50,500,25000),
('677eb80c7a165','Delta VFD Drive','0.5HP',8504,2,9000,18000),
('677eb8aff273c','HP Solvent Cartridge','47ml',8443,10,1200,12000),
('677f497c81839','Multispan Counter','Digital counter',9029,5,1700,8500),
('677f7a4bbdd86','Conveyor Belt','SS make 300mm',4010,2,11000,22000);

CREATE TABLE "purchaseinv2" (
  "nid"         INTEGER PRIMARY KEY AUTOINCREMENT,
  "invid"       TEXT NOT NULL,
  "cid"         INTEGER NOT NULL,
  "invdate"     TEXT NOT NULL,
  "orderid"     TEXT NOT NULL,
  "totalitems"  INTEGER NOT NULL,
  "subtotal"    INTEGER NOT NULL,
  "taxrate"     INTEGER NOT NULL,
  "taxamount"   INTEGER NOT NULL,
  "totalamount" INTEGER NOT NULL,
  "created"     TEXT NOT NULL
);
INSERT INTO "purchaseinv2" VALUES
(1,'PUR/24-25/0001',21,'2024-05-10','677eb7ba2e3c8',1,25000,18,4500,29500,'2024-05-10 10:30:00'),
(2,'PUR/24-25/0002',22,'2024-07-18','677eb80c7a165',2,18000,18,3240,21240,'2024-07-18 14:15:00'),
(3,'PUR/24-25/0003',23,'2024-09-25','677eb8aff273c',1,12000,18,2160,14160,'2024-09-25 11:45:00'),
(4,'PUR/24-25/0004',24,'2024-11-12','677f497c81839',3,8500,18,1530,10030,'2024-11-12 16:20:00'),
(5,'PUR/24-25/0005',25,'2025-01-06','677f7a4bbdd86',1,22000,18,3960,25960,'2025-01-06 09:50:00');

-- =====================================================================
-- QUICK QUOTES
-- =====================================================================

CREATE TABLE "quickquote" (
  "sr_no"     INTEGER PRIMARY KEY AUTOINCREMENT,
  "q_id"      TEXT NOT NULL,
  "p_id"      INTEGER NOT NULL,
  "mob"       TEXT NOT NULL,
  "quantity"  TEXT NOT NULL,
  "price"     TEXT NOT NULL,
  "subtotal"  INTEGER NOT NULL,
  "gst"       INTEGER NOT NULL,
  "total"     INTEGER NOT NULL,
  "created"   TEXT NOT NULL
);
INSERT INTO "quickquote" ("q_id","p_id","mob","quantity","price","subtotal","gst","total","created") VALUES
('QUICK/24-25/0001',2,'7412589630','1','650',650,117,767,'2024-06-15'),
('QUICK/24-25/0002',4,'7485610230','1','5000',5000,900,5900,'2024-07-22'),
('QUICK/24-25/0003',4,'7485961023','1','50',50,9,59,'2024-08-10'),
('QUICK/24-25/0004',1,'9632587410','1','55',55,10,65,'2024-09-05'),
('QUICK/24-25/0005',75,'7412589630','1','40',40,7,47,'2024-10-18'),
('QUICK/24-25/0006',43,'8735003590','1','50000',50000,9000,59000,'2024-11-28'),
('QUICK/24-25/0007',4,'8760152410','1','500',500,90,590,'2024-12-15'),
('QUICK/24-25/0008',1,'8735003590','1','450',450,81,531,'2025-01-08'),
('QUICK/24-25/0009',1,'7016419537','1','500',500,90,590,'2025-01-08'),
('QUICK/24-25/0010',1,'8735003590','1','500',500,90,590,'2025-01-08'),
('QUICK/24-25/0011',4,'8735003590','1','30000',30000,5400,35400,'2025-01-08'),
('QUICK/24-25/0012',1,'7600158240','1','50',50,9,59,'2025-01-08'),
('QUICK/24-25/0013',4,'8735003590','1','500',500,90,590,'2025-01-08');

-- =====================================================================
-- QUOTATIONS
-- =====================================================================

CREATE TABLE "quote" (
  "orderno"   INTEGER PRIMARY KEY AUTOINCREMENT,
  "orderid"   TEXT NOT NULL,
  "item_name" TEXT NOT NULL,
  "quantity"  INTEGER NOT NULL,
  "price"     INTEGER NOT NULL,
  "total"     INTEGER NOT NULL
);
INSERT INTO "quote" ("orderid","item_name","quantity","price","total") VALUES
('677eb8506b620','CT-01 HandHeld Manual Coder',1,4500,4500),
('677f583470f5f','CT-05 Table Top Coder',1,12000,12000),
('677f584a5b6c7','CT-02 Handy Marker',1,8500,8500),
('677f585b6c7d8','CT-07 Multipurpose Coder',3,22000,66000),
('677f586c7d8e9','CT-07 Ice Cream Coder',1,65000,65000);

CREATE TABLE "quote2" (
  "invid"       TEXT PRIMARY KEY,
  "cid"         INTEGER NOT NULL,
  "orderid"     TEXT NOT NULL,
  "totalitems"  INTEGER NOT NULL,
  "subtotal"    INTEGER NOT NULL,
  "taxrate"     INTEGER NOT NULL,
  "taxamount"   INTEGER NOT NULL,
  "totalamount" INTEGER NOT NULL,
  "created"     TEXT NOT NULL,
  "note"        TEXT NOT NULL
);
INSERT INTO "quote2" VALUES
('QT/24-25/0001',4,'677eb8506b620',1,4500,18,810,5310,'2024-03-10','Validity: 30 days'),
('QT/24-25/0002',7,'677f583470f5f',2,12000,18,2160,14160,'2024-04-18','Bulk order discount applicable'),
('QT/24-25/0003',9,'677f584a5b6c7',1,8500,18,1530,10030,'2024-06-25',''),
('QT/24-25/0004',12,'677f585b6c7d8',3,22000,18,3960,25960,'2024-09-14','Delivery in 2 weeks'),
('QT/24-25/0005',14,'677f586c7d8e9',1,65000,18,11700,76700,'2024-11-30','Includes installation');

-- =====================================================================
-- PRODUCT SPECS
-- =====================================================================

CREATE TABLE "techsps" (
  "tid"     INTEGER PRIMARY KEY AUTOINCREMENT,
  "p_id"    INTEGER NOT NULL,
  "img_loc" TEXT,
  "techs"   TEXT,
  "subcat"  TEXT
);
INSERT INTO "techsps" ("p_id","img_loc","techs","subcat") VALUES
(1,'hand stamp.jpg','Printing Area : 35 x 60 mm (LxB);Prints using Grooves Rubber based stereo (3  MM); Ink- Fast dry & Water Resistant; Weight 0.5 kgs; Comes with 500ml ink, 500ml Cleaner, Groove fonts & Inkpad (2pcs)','Manual Batch Coding Machine'),
(2,'handy box.jpg','Printing Area : 3x12 inch (LxB);Prints using Grooves Rubber based stereo (12  MM); Ink Roller – Rechargeable high capacity porous ink;Impression -  1,000 per charge of 20ml / 40ml. /10 ml(depending upon no. of lines printed);Weight - 3kgs;Comes with 1 liter porus ink.','Manual Batch Coding Machine'),
(3,'handy bag.jpg','Printing Area : 3x12 inch (LxB);Prints using Grooves Rubber based stereo (12  MM);Ink Roller – Rechargeable high capacity non porous ink;Impression -  1,000 per charge of 20ml / 40ml. /10 ml. (depending upon no. of lines printed);Weight - 3kgs;Comes with 1 liter HDPE ink, 1 Liter ink-aid & Tools.','Manual Batch Coding Machine'),
(4,'table top.jpg','Printing Area – 35 x 35 mm (LxB);Operating Method – Foot Switch & Continuous Both.;Power – 230 V AC 50 Hz;Print material: rubber stereo 3 mm sheet.;Comes with -  PLC motor, Liquid Fast dry Ink(500 ml),ink Roll, Form Pad, Tools, Circuit Board controller, Cleaner(500 ml).; Printing Speed (Max) - 60 Nos/Min.;Comes with Complete protective box','Semi Automatic Batch Coding Machine'),
(87,'handheld inkjet.jpg','Max.Print Height : 12.7 mm;Max. Speed : 30-40 per/min.;LCD Display with print head;Comes along pen drive, ink cartridge, charger, SS Frame & Battery;1 year warranty;NO Courier Charges','Handy Inkjet Printer'),
(5,'2in1.jpg','Overall Dimensions: 1070 x 680 x 450;Speed: 150 cartons/min.  250 labels/min.;Pouch/Carton Size: 80mm x 40mm to 305mm x 200mm;Power : 0.5HP  3 phase;Weight: Approx. 100 Kgs;Prints using Rubber Stereo.;Materials along with m/c: 500ml paste Ink, tape roll,Tools.','Automatic Batch Coding Machine'),
(76,'Handheld inkjet printer.jpg','Max.Print Height : 12. 7 mm;Max. Speed : 30-40 per/min.;LCD Display with print head;Comes along pen drive, ink cartridge, charger, SS Frame & Battery;1 year warranty;NO Courier Charges','Handy Inkjet Printer'),
(7,'2in1.jpg','Overall Dimensions: 1070 x 680 x 450;Speed: 150 cartons/min.  250 labels/min.;Pouch/Carton Size: 80mm x 40mm to 305mm x 200mm;Power : 0.5HP  3 phase;Weight: Approx. 100 Kgs;Prints using Rubber Stereo.;Materials along with m/c: 500ml paste Ink, tape roll,Tools.','Automatic Batch Coding Machines'),
(6,'2in1.jpg','Overall Dimensions: 1070 x 680 x 450;Speed: 150 cartons/min.  250 labels/min.;Pouch/Carton Size: 80mm x 40mm to 305mm x 200mm;Power : 0.5HP  3 phase;Weight: Approx. 100 Kgs;Prints using Rubber Stereo.;Materials along with m/c: 500ml paste Ink, tape roll,Tools.','Automatic Batch Coding Machines'),
(81,'table top.jpg','Printing Area – 35 x 35 mm (LxB);Operating Method – Foot Switch & Continuous Both.;Power – 230 V AC 50 Hz;Print material: rubber stereo 3 mm sheet.;Comes with -  PLC motor, Liquid Fast dry Ink(500 ml),ink Roll, Form Pad, Tools, Circuit Board controller, Cleaner(500 ml).; Printing Speed (Max) - 60 Nos/Min.;Comes with Complete protective box','Semi Automatic Batch Coding Machine'),
(8,'standard carton.jpg','Overall Dimensions: 1010 x 690 x 590;Speed:   250 cartons/min.;Carton Size: 80mm x 25mm to 305mm x 200mm;Power : 0.5HP  3 phase;Weight: Approx. 102 Kgs;Prints using Rubber Stereo.;Materials along m/c:  500ml paste Ink, tape roll,Liquid block, Tools & Liquid ink.','Automatic Batch coding Machine'),
(43,'standard label.jpg','Overall Dimensions: 880 x 530 x 460;Speed:  250 labels/min.;Label Size: 20mm x 40mm to 150mm x 200mm;Power: 0.5HP  3 phase;Weight: Approx. 80 Kgs;Prints using Rubber Stereo.;Materials along with machine: Paste ink, 2 sided tape,Tools & Feeding Rubber ','Automatic Batch coding Machine'),
(131,'mini printer.jpg','Max.Print Height : 12.7 mm;Max. Speed : 30-40 per/min.;LCD  Display;Comes along pen drive , HP original Seal Pack Black ink Cartridge , charger;NO Courier Charges','Handy Inkjet Printer'),
(75,'hp cartridge.jpg','47 ml Ink Cartridge;No chip Cartridge;HP Original Seal Pack Cartridge;Print Head 12.7mm;Solvent Ink;Fast Dry & Permanent ','Handy Inkjet Printer'),
(88,'hp cartridge.jpg','47 ml Ink Cartridge;No chip Cartridge;HP Original Seal Pack Cartridge;Print Head 12.7mm;Solvent Ink;Fast Dry & Permanent ','Handy Inkjet Printer'),
(98,'double bond.jpg','Japanese Cartridge;High cohesion on Glossy Surface;Permanent impression Guaranteed;Print material: Glossy surface, Glass bottles etc','Handy Inkjet Printer'),
(100,'simple conveyor.jpeg','Machine Length - 1500 mm; Machine Width -  350 mm;Conveyor Belt Width – 300 mm;Fully SS Make;0.25 HP Motor with Speed Controller;Completely Foldable type','conveyor'),
(113,'simple conveyor.jpeg','Machine Length - 1500 mm; Machine Width -  350 mm;Conveyor Belt Width – 300 mm;Fully SS Make;0.25 HP Motor with Speed Controller;Completely Foldable type','conveyor'),
(78,'m 302.jpg','Max.Print Height : 12.7 mm;Max. Speed : 80-200 per/min. (depends upon the size of samples);LCD  Display with print head;Comes along pen drive,Solvent Ink (Black) cartridge & charger.;Comes with Additional Stand assembly for attachment in conveyor & Metal sensor; Unlock Machine;1 year warranty','Online Printers'),
(124,'m 302.jpg','Max.Print Height : 12.7 mm;Max. Speed : 80-200 per/min. (depends upon the size of samples);LCD  Display with print head;Comes along pen drive,Solvent Ink (Black) cartridge & charger.;Comes with Additional Stand assembly for attachment in conveyor & Metal sensor; Unlock Machine;1 year warranty','Online Printers'),
(105,'m 302.jpg','Max.Print Height : 12.7 mm;Max. Speed : 80-200 per/min. (depends upon the size of samples);LCD  Display with print head;Comes along pen drive,Solvent Ink (Black) cartridge & charger.;Comes with Additional Stand assembly for attachment in conveyor & Metal sensor; Unlock Machine;1 year warranty','Online Printers'),
(109,'m 302.jpg','Max.Print Height : 12.7 mm;Max. Speed : 80-200 per/min. (depends upon the size of samples);LCD  Display with print head;Comes along pen drive,Solvent Ink (Black) cartridge & charger.;Comes with Additional Stand assembly for attachment in conveyor & Metal sensor; Unlock Machine;1 year warranty','Online Printers'),
(136,'CT 13.jpeg','Max.Print Height : 50 mm [Each head 25 mm];Max. Speed : 120-300 per/min. (depends upon the size of samples);LCD  Display with print head;Comes along pen drive, Solvent Ink (Black) cartridge & Power charger.;Comes with Additional Stand assembly for attachment in conveyor & Metal sensor;1 year warranty','Online Printers');

-- =====================================================================
-- INDEXES
-- =====================================================================

CREATE INDEX idx_client_name       ON client(c_name);
CREATE INDEX idx_client_gst        ON client(gst);
CREATE INDEX idx_account_cid       ON account(cid);
CREATE INDEX idx_products_cattype  ON products(cattype);
CREATE INDEX idx_products_ptype    ON products(p_type);
CREATE INDEX idx_invtest2_cid      ON invtest2(cid);
CREATE INDEX idx_invtest2_created  ON invtest2(created);
CREATE INDEX idx_invtest_orderid   ON invtest(orderid);
CREATE INDEX idx_paidhistory_cid   ON paidhistory(cid);
CREATE INDEX idx_purchaseinv2_cid  ON purchaseinv2(cid);
CREATE INDEX idx_quote2_cid        ON quote2(cid);
CREATE INDEX idx_protest2_cid      ON protest2(cid);
CREATE INDEX idx_delivery_invid    ON delivery_addresses(invid);
CREATE INDEX idx_techsps_pid       ON techsps(p_id);

COMMIT;
PRAGMA foreign_keys = ON;