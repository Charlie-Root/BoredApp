
-- Part 1 Create the Database
CREATE DATABASE BoredApp_users;
USE BoredApp_users;



-- Part 1/2 Creating the Database Table
CREATE TABLE the_users (
    UserID INT AUTO_INCREMENT NOT NULL,
    FirstName VARCHAR(65) NOT NULL,
    LastName VARCHAR(65) NOT NULL,
    Email VARCHAR(65) NOT NULL UNIQUE,
    DOB DATETIME NOT NULL,
    City VARCHAR(200) NOT NULL,
    Username VARCHAR(200) NOT NULL,
    Password VARCHAR(200) NOT NULL,
    CONSTRAINT pk_the_users PRIMARY KEY (UserID),
    INDEX ix_the_users_Email (Email),
    INDEX ix_the_users_Username (Username)
);


-- Part 2/2 Creating the Database Table
CREATE TABLE favourites (
    activityID INT NOT NULL,
    UserID INT NOT NULL,
    activity VARCHAR(200) NOT NULL,
    participants INT NOT NULL,
    price FLOAT NOT NULL,
    type VARCHAR(200) NOT NULL,
    CONSTRAINT pk_favourites PRIMARY KEY (activityID),
    CONSTRAINT fk_favourites_the_users FOREIGN KEY (UserID) REFERENCES the_users(UserID),
    INDEX ix_favourites_activityID_UserID (activityID, UserID)
);