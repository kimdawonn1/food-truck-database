-- =========================================================
-- Original ad hoc business-question queries from the source
-- database management course project (MySQL dialect).
-- Preserved here for reference; the automated equivalents of
-- several of these now live as views in scripts/load_and_transform.py
-- =========================================================

-- 1. Who is the head boss of the Lex Mex food truck employees?
SELECT e.employeeID, e.empFN AS firstName, e.empLN AS lastName
FROM Employee e
WHERE e.truckID = (SELECT truckID FROM Truck WHERE restaurantName = 'Lex Mex')
  AND e.bossID IS NULL;

-- 2. List all the orders from customers that have not signed up for the loyalty program.
SELECT orderID, customerFN, customerLN
FROM `order` LEFT JOIN customer USING(customerID)
WHERE loyaltyNumber IS NULL;

-- 3. What are the most popular menu items ordered from each of the food trucks?
SELECT truck.truckID, truck.restaurantName, menu_item.menuItemID, menu_item.menuItemName,
       SUM(order_has_menu_item.quantity) AS totalQuantityOrdered
FROM truck
JOIN menu_item ON truck.truckID = menu_item.truckID
JOIN order_has_menu_item ON menu_item.menuItemID = order_has_menu_item.menuItemID
GROUP BY truck.truckID, truck.restaurantName, menu_item.menuItemID, menu_item.menuItemName
ORDER BY truck.truckID, totalQuantityOrdered DESC;

-- 4. What are the names of the most regular customers of each food truck between now and 2023?
SELECT truck.restaurantName, customer.customerFN, customer.customerLN, COUNT(orderID) AS orderCount
FROM truck
JOIN customer USING(truckID)
JOIN `order` USING(customerID)
WHERE orderDate BETWEEN '2023-01-01' AND CURDATE()
GROUP BY truckID, customerID
HAVING COUNT(`order`.orderID) = (
  SELECT MAX(orderCount) FROM (
    SELECT COUNT(`order`.orderID) AS orderCount
    FROM truck
    JOIN customer USING(truckID)
    JOIN `order` USING(customerID)
    WHERE orderDate BETWEEN '2023-01-01' AND CURDATE()
    GROUP BY truck.truckID, `order`.customerID
  ) AS Subquery
)
ORDER BY orderCount DESC;

-- 5. Are there any menu items that are not found in any orders this month?
SELECT mi.menuItemID, mi.menuItemName, mi.truckID
FROM Menu_Item mi
WHERE mi.menuItemID NOT IN (
  SELECT DISTINCT ohmi.menuItemID
  FROM Order_Has_Menu_Item ohmi
  JOIN `order` o ON ohmi.orderID = o.orderID
  WHERE MONTH(o.orderDate) = MONTH(CURDATE())
    AND YEAR(o.orderDate) = YEAR(CURDATE())
);

-- 6. For Mr. H's Donuts, list all customers with orders that have only donuts as menu items.
SELECT c.customerFN AS firstName, c.customerLN AS lastName
FROM Customer c
JOIN `Order` o ON c.customerID = o.customerID
JOIN Order_Has_Menu_Item ohmi ON o.orderID = ohmi.orderID
JOIN Menu_Item mi ON ohmi.menuItemID = mi.menuItemID
WHERE mi.truckID = (SELECT truckID FROM Truck WHERE restaurantName = 'Mr. H\'s Donuts')
GROUP BY c.customerID, c.customerFN, c.customerLN
HAVING COUNT(DISTINCT mi.menuItemID) =
       COUNT(DISTINCT CASE WHEN mi.menuItemName REGEXP 'donut|doughnut' THEN mi.menuItemID END);

-- 7. Which trucks have the most inventory items expiring in the next month?
SELECT t.truckID, t.restaurantName, COUNT(i.itemID) AS expiringItemCount
FROM Truck t
JOIN Inventory i ON t.truckID = i.truckID
WHERE i.expirationDate BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 1 MONTH)
GROUP BY t.truckID, t.restaurantName
ORDER BY expiringItemCount DESC;

-- 8. How many employees get paid more than their boss, and what trucks do they work at?
SELECT t.restaurantName AS truckName, COUNT(e.employeeID) AS employeesPaidMoreThanBoss
FROM Employee e
JOIN Employee boss ON e.bossID = boss.employeeID
JOIN Truck t ON e.truckID = t.truckID
WHERE e.empSalary > boss.empSalary
GROUP BY t.restaurantName;

-- 9. Which food truck has the most menu items?
SELECT truck.truckID, truck.restaurantName, COUNT(DISTINCT menu_item.menuItemID) AS menuItemCount
FROM Truck
LEFT JOIN Menu_Item ON truck.truckID = menu_item.truckID
GROUP BY truck.truckID, truck.restaurantName
HAVING COUNT(DISTINCT menu_item.menuItemID) = (
  SELECT MAX(menuItemCount) FROM (
    SELECT COUNT(DISTINCT menu_item.menuItemID) AS menuItemCount
    FROM Truck
    LEFT JOIN Menu_Item ON truck.truckID = menu_item.truckID
    GROUP BY truck.truckID
  ) AS counts
);

-- 10. Which customer placed the order bringing in the most points, and on what day?
SELECT customerFN, customerLN, orderID, orderDate, points
FROM `Order`
JOIN Customer USING(customerID)
WHERE points = (SELECT MAX(points) FROM `Order`);
