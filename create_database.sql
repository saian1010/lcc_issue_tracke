CREATE DATABASE lcc_issue_tracke if not exists;
USE lcc_issue_tracke;
drop table users;

-- users
CREATE TABLE users (
    user_id INT NOT NULL AUTO_INCREMENT,
    username VARCHAR(20) NOT NULL,
    password_hash CHAR(60) BINARY NOT NULL,
    email VARCHAR(320) NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    location VARCHAR(50) NOT NULL,
    profile_image VARCHAR(255),
    role ENUM('visitor', 'helper', 'admin') NOT NULL,
    status ENUM('active', 'inactive') NOT NULL,
    PRIMARY KEY (user_id)
);

-- issues
CREATE TABLE issues (
    issue_id INT NOT NULL AUTO_INCREMENT,
    user_id INT NOT NULL,
    summary VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    status ENUM('new', 'open', 'stalled', 'resolved') NOT NULL,
    PRIMARY KEY (issue_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- comments
CREATE TABLE comments (
    comment_id INT NOT NULL AUTO_INCREMENT,
    issue_id INT NOT NULL,
    user_id INT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    PRIMARY KEY (comment_id),
    FOREIGN KEY (issue_id) REFERENCES issues(issue_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);