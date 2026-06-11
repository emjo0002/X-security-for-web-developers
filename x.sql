-- phpMyAdmin SQL Dump
-- version 5.2.2
-- https://www.phpmyadmin.net/
--
-- Host: mariadb
-- Generation Time: Jun 11, 2026 at 03:35 AM
-- Server version: 10.6.20-MariaDB-ubu2004
-- PHP Version: 8.2.27

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `x`
--
CREATE DATABASE IF NOT EXISTS `x` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE `x`;

-- --------------------------------------------------------

--
-- Table structure for table `bookmarks`
--

CREATE TABLE `bookmarks` (
  `bookmark_user_fk` char(32) NOT NULL,
  `bookmark_post_fk` char(32) NOT NULL,
  `bookmarked_at` bigint(20) UNSIGNED NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `bookmarks`
--

INSERT INTO `bookmarks` (`bookmark_user_fk`, `bookmark_post_fk`, `bookmarked_at`) VALUES
('4542f5410310486b9efecc4934e1a643', '6fb859f7093543148f922a08ddd649a3', 1781131874),
('a5d53c2b385341e88b644a1bbbd8e131', '5c4a1ea51cc2472cbe27f030c2073b2e', 1765280007),
('b09b7853689b490a9c1e093b0507dc8b', '3480c1614d6f44d59534f5da6f38cf56', 1765281819);

-- --------------------------------------------------------

--
-- Table structure for table `comments`
--

CREATE TABLE `comments` (
  `comment_pk` char(32) NOT NULL,
  `comment_post_fk` char(32) NOT NULL,
  `comment_user_fk` char(32) NOT NULL,
  `comment_text` text NOT NULL,
  `comment_updated_at` bigint(20) NOT NULL,
  `comment_created_at` bigint(20) UNSIGNED NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `comments`
--

INSERT INTO `comments` (`comment_pk`, `comment_post_fk`, `comment_user_fk`, `comment_text`, `comment_updated_at`, `comment_created_at`) VALUES
('91db41a460c6431a929d97ba52b25922', '6fb859f7093543148f922a08ddd649a3', '4542f5410310486b9efecc4934e1a643', 'I can still see it hehe', 0, 1781131872),
('b48c8e9498a24463919d3fdfc727d13d', 'd7d810e76ed845a9aae051e0189495e7', 'b09b7853689b490a9c1e093b0507dc8b', 'Messi is better btw;)', 0, 1765281846),
('ba22fc97ef46476a99513d0e8fe29e55', 'c4fa0640c5784ff1af6ac0ac06b03997', 'a5d53c2b385341e88b644a1bbbd8e131', 'Welcome aboard, buddy!', 0, 1765279985);

--
-- Triggers `comments`
--
DELIMITER $$
CREATE TRIGGER `after_comment_delete` AFTER DELETE ON `comments` FOR EACH ROW BEGIN
    UPDATE `posts`
    SET `post_total_comments` = GREATEST(0, CAST(`post_total_comments` AS SIGNED) - 1)
    WHERE `post_pk` = OLD.comment_post_fk;
END
$$
DELIMITER ;
DELIMITER $$
CREATE TRIGGER `after_comment_insert` AFTER INSERT ON `comments` FOR EACH ROW BEGIN
    UPDATE `posts`
    SET `post_total_comments` = `post_total_comments` + 1
    WHERE `post_pk` = NEW.comment_post_fk;
END
$$
DELIMITER ;

-- --------------------------------------------------------

--
-- Table structure for table `follows`
--

CREATE TABLE `follows` (
  `follow_follower_fk` char(32) NOT NULL,
  `follow_followed_fk` char(32) NOT NULL,
  `follow_timestamp` int(10) UNSIGNED DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `follows`
--

INSERT INTO `follows` (`follow_follower_fk`, `follow_followed_fk`, `follow_timestamp`) VALUES
('9860c6174a3141c5b1e7c8b3638b2f2b', '88a93bb5267e443eb0047f421a7a2f34', 1765100873),
('b09b7853689b490a9c1e093b0507dc8b', '9860c6174a3141c5b1e7c8b3638b2f2b', 1765281336),
('fe9715d110534b17a9dc36e1f8dfd43c', 'b09b7853689b490a9c1e093b0507dc8b', 1780952007);

-- --------------------------------------------------------

--
-- Table structure for table `likes`
--

CREATE TABLE `likes` (
  `like_user_fk` char(32) NOT NULL,
  `like_post_fk` char(32) NOT NULL,
  `like_timestamp` bigint(20) UNSIGNED NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `likes`
--

INSERT INTO `likes` (`like_user_fk`, `like_post_fk`, `like_timestamp`) VALUES
('a5d53c2b385341e88b644a1bbbd8e131', '3480c1614d6f44d59534f5da6f38cf56', 1765280013),
('a5d53c2b385341e88b644a1bbbd8e131', '5c4a1ea51cc2472cbe27f030c2073b2e', 1765280004),
('b09b7853689b490a9c1e093b0507dc8b', '3480c1614d6f44d59534f5da6f38cf56', 1765280046),
('b09b7853689b490a9c1e093b0507dc8b', 'c4fa0640c5784ff1af6ac0ac06b03997', 1765280042);

--
-- Triggers `likes`
--
DELIMITER $$
CREATE TRIGGER `after_like_delete` AFTER DELETE ON `likes` FOR EACH ROW BEGIN
    UPDATE `posts` 
    SET `post_total_likes` = GREATEST(0, CAST(`post_total_likes` AS SIGNED) - 1)
    WHERE `post_pk` = OLD.like_post_fk;
END
$$
DELIMITER ;
DELIMITER $$
CREATE TRIGGER `after_like_insert` AFTER INSERT ON `likes` FOR EACH ROW BEGIN
    UPDATE `posts` 
    SET `post_total_likes` = `post_total_likes` + 1 
    WHERE `post_pk` = NEW.like_post_fk;
END
$$
DELIMITER ;

-- --------------------------------------------------------

--
-- Table structure for table `posts`
--

CREATE TABLE `posts` (
  `post_pk` char(32) NOT NULL,
  `post_user_fk` char(32) NOT NULL,
  `post_message` varchar(280) NOT NULL,
  `post_total_likes` int(11) NOT NULL DEFAULT 0,
  `post_total_comments` int(11) NOT NULL DEFAULT 0,
  `post_media_path` varchar(255) NOT NULL,
  `post_blocked_at` bigint(20) DEFAULT NULL,
  `post_deleted_at` bigint(20) NOT NULL,
  `post_updated_at` bigint(20) NOT NULL,
  `post_created_at` int(11) NOT NULL,
  `post_visibility` enum('public','private') NOT NULL DEFAULT 'public'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `posts`
--

INSERT INTO `posts` (`post_pk`, `post_user_fk`, `post_message`, `post_total_likes`, `post_total_comments`, `post_media_path`, `post_blocked_at`, `post_deleted_at`, `post_updated_at`, `post_created_at`, `post_visibility`) VALUES
('3480c1614d6f44d59534f5da6f38cf56', '9860c6174a3141c5b1e7c8b3638b2f2b', 'I don\'t know why, but I like sofas so much, I have made my profile picture a sofa-cushion :)', 2, 0, '', 0, 0, 0, 1765278686, 'public'),
('5c4a1ea51cc2472cbe27f030c2073b2e', 'b09b7853689b490a9c1e093b0507dc8b', 'I\'m so happy that Malthe finally spoke out about his love for sofas! Honesty is good!', 1, 0, '', 0, 0, 0, 1765278933, 'public'),
('6fb859f7093543148f922a08ddd649a3', 'b09b7853689b490a9c1e093b0507dc8b', 'This is private hehe', 0, 1, '', 0, 0, 1781131824, 1781129016, 'private'),
('707c22f2362f4d7b8717535096223199', 'b09b7853689b490a9c1e093b0507dc8b', '<script>alert(1)</script>', 0, 0, '', 0, 0, 0, 1781132011, 'public'),
('85a3d8a9864b47298290aa90576b9285', '88a93bb5267e443eb0047f421a7a2f34', 'Hi. I\'m Gustav. I am a medieval time-traveller!', 0, 0, '', 0, 0, 0, 1765278640, 'public'),
('c4fa0640c5784ff1af6ac0ac06b03997', '12d6e25ee4a1401d9e5575d6319ce496', 'I\'m new to X, so be kind!', 1, 1, '', 0, 0, 0, 1765278470, 'public'),
('d7d810e76ed845a9aae051e0189495e7', 'a5d53c2b385341e88b644a1bbbd8e131', 'I\'m such a big Cristiano Ronaldo SUIIII fan!', 0, 1, 'images/294f19dc9b784be2a422368ca964f574_cristi.jpg', 0, 0, 0, 1765279953, 'public'),
('ebfce8bbac524094b3a9fa169f6eb029', '87df12f908664075aa97a68cb4f5280f', 'I\'m the president!!', 0, 0, '', 0, 0, 0, 1765280856, 'public'),
('fddbc0c31c63431e8fd5ff8fc63e7aea', 'a5d53c2b385341e88b644a1bbbd8e131', 'I swear to god, I hate Chelsea & Arsenal fans! They\'re so fucking stubborn GRRRRRR ARGHHH', 0, 0, '', 1765280414, 0, 0, 1765280365, 'public');

-- --------------------------------------------------------

--
-- Table structure for table `trends`
--

CREATE TABLE `trends` (
  `trend_pk` char(32) NOT NULL,
  `trend_title` varchar(100) NOT NULL,
  `trend_message` varchar(100) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `trends`
--

INSERT INTO `trends` (`trend_pk`, `trend_title`, `trend_message`) VALUES
('6543c885d1af4ebcbd5280a4afaa1e2c', 'Computing & Software', 'Lenovo launch scroll-able screen laptops'),
('6543c995d02f4ebcbd5280a4afaa1e2c', 'Sports', 'The World Cup will be hosted in USA for 2026'),
('6543c995d1af423cbd5280a4afaa1e2c', 'World news', 'China enforces new bill to pass taxation laws'),
('6543c995d1af4ebcb76280a4afaa1e2c', 'Education', 'KEA & CPH Business merge to be EK'),
('6543c995d1af4ebcbd5280a4afaa1e2c', 'Politics are rotten', 'Everyone talks and only a few try to do something'),
('6543c995d1af4ebcbd52ola4afaa1e2c', 'War & politics', 'War is currently raging in Sudan'),
('6543c995d1oa4ebcbd5280a4afaa1e2c', 'Stocks', 'Novo Stocks take a beating this morning'),
('6543c995puaf4ebcbd5280a4afaa1e2c', 'Coding & design', 'PythonAnywhere servers are down'),
('8343c995d1af4ebcbd5280a6afaa1e2d', 'New rocket to the moon', 'A new rocket has been sent towards the moon, but id didn\'t make it');

-- --------------------------------------------------------

--
-- Table structure for table `users`
--

CREATE TABLE `users` (
  `user_pk` char(32) NOT NULL,
  `user_email` varchar(100) NOT NULL,
  `user_password` varchar(255) NOT NULL,
  `user_password_reset_key` char(32) DEFAULT NULL,
  `user_username` varchar(20) NOT NULL,
  `user_first_name` varchar(20) NOT NULL,
  `user_last_name` varchar(20) NOT NULL DEFAULT '',
  `user_avatar_path` varchar(255) NOT NULL,
  `user_verification_key` char(32) NOT NULL,
  `user_verified_at` bigint(20) UNSIGNED NOT NULL,
  `user_deleted_at` bigint(20) UNSIGNED NOT NULL,
  `user_is_admin` tinyint(1) NOT NULL DEFAULT 0,
  `user_blocked_at` bigint(20) UNSIGNED NOT NULL DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `users`
--

INSERT INTO `users` (`user_pk`, `user_email`, `user_password`, `user_password_reset_key`, `user_username`, `user_first_name`, `user_last_name`, `user_avatar_path`, `user_verification_key`, `user_verified_at`, `user_deleted_at`, `user_is_admin`, `user_blocked_at`) VALUES
('12d6e25ee4a1401d9e5575d6319ce496', 'dimidummy9@gmail.com', 'scrypt:32768:8:1$meYtqAjbJ8n8lH7D$3018ed792aac88da18034e27c83fde5ca0483a4c893d11c4e3ad33bad8679596236a818d2886d1634dafbbadb84deef600e755240d28260090394245f4f1cffc', '', 'DimiDev', 'Dimitrios', 'Baltzis', 'static/images/avatars/be2a92fe09ee44d386fe1d1b8639c31b.jpeg', '', 1765277199, 0, 0, 0),
('4542f5410310486b9efecc4934e1a643', 'admin@admin.com', 'scrypt:32768:8:1$EFEjABUNz76czrxL$257fd3bbaaa2e7169dcb3dd291ba42fa16f20a7d20753577d81021f3ac2ed95c7f5925e7a92f8eecffb8dee5b8c060379f10e13f1911d99efcaf66e8f9f1323a', '', 'admin', 'Admin', 'AdminAdmin', 'static/images/avatars/unknown.jpg', '', 12321321, 0, 1, 0),
('87df12f908664075aa97a68cb4f5280f', 'trump@gmail.com', 'scrypt:32768:8:1$SRkGmSc4UmG1PWo4$96a541a53c0945a1d5f4b8ebc2b2c1cf2f0b8cf749708547b71bb5ecfcaafc59706931ec5cb20fd538171467e93a80e9281aa8277f65d7cfd8881d17221a9fa6', '', 'POTUS', 'Donald', 'Trump', 'static/images/avatars/ca80cfeef9ed49948c3e48f8c3e78b6e.jpg', '', 1765277199, 0, 0, 1765281053),
('88a93bb5267e443eb0047f421a7a2f34', 'santi@gmail.com', 'scrypt:32768:8:1$PEIO0eliDPqnCCbw$acb791128831bc90030ac363e4b76db196689bd99c1ccde5c2c20a7d4fe909e07129f3f4fd4f086e347375edbb8229e9ba5dc126cc14f6107fb1fc2abf6498f8', NULL, 'GustavDev', 'Gustav', 'Larsen', 'static/images/avatars/b03959e8afd84bdd9270fcaca03810d7.jpg', '', 54654564, 0, 0, 0),
('9860c6174a3141c5b1e7c8b3638b2f2b', 'maltheaaen@gmail.com', 'scrypt:32768:8:1$5NSH8Gsqi83lQV24$b61989755f5e00e7632463dee7b806b93acab7d4de36b6e32caf47a2fcef8bf23db0624a3767d5bae3ba40c77673171dad51a4b472e44a9463fc141a0b7f37bb', NULL, 'Malt', 'Malthe', 'Aaen', 'static/images/avatars/a646c5c464854943b27d7c07c0074fb8.png', '', 54654564, 0, 0, 0),
('a5d53c2b385341e88b644a1bbbd8e131', 'r@r.dk', 'scrypt:32768:8:1$0RU5B87Om1vuTrj5$19c6e65314a2bb8b96444834b1901e1cd38594bfaaf85ae378034f8978e0338ed0b7d3076d26545b0ed176fa1a10c503b4ff2f7807ac5164703cddc315d583fd', '', 'RasmusOlsen', 'Rasmus', 'Olsen', 'static/images/avatars/882972796125456fb54ec7ff1109804e.jpg', '', 1765277199, 0, 0, 0),
('b09b7853689b490a9c1e093b0507dc8b', 'emil.johansson2@gmail.com', 'scrypt:32768:8:1$OGl7y8BaCfoVx7xc$7ed1d28e8ab742516d793102dc43d5056f59dcdb5a46689925702e3a41bee1a7a534a54dbbc08d98f8f10d80e306bc09f5826451e308284e1151b1636f3e305b', '', 'DevEmil', 'Emil', 'Johansson', 'static/images/avatars/b54e32cb4a054b1cb3b2da9821580653.jpg', '', 54654564, 0, 0, 0),
('fe9715d110534b17a9dc36e1f8dfd43c', 'emjo0002@stud.kea.dk', 'scrypt:32768:8:1$jIUdJNvmKkfPEPyK$ee34500bde95557468ca80a00aa0ce226fe0e6191b6a3710781b15799a119f6c9e124490a552af7ad3989fe8b95b18fd161be65fd974b517c3aa08fc17cf95ef', '', 'emil8883', 'Emil', 'Johansson', 'static/images/avatars/unknown.jpg', '', 1765277199, 1780952655, 0, 0);

--
-- Indexes for dumped tables
--

--
-- Indexes for table `bookmarks`
--
ALTER TABLE `bookmarks`
  ADD PRIMARY KEY (`bookmark_user_fk`,`bookmark_post_fk`),
  ADD KEY `bookmark_post_fk` (`bookmark_post_fk`);

--
-- Indexes for table `comments`
--
ALTER TABLE `comments`
  ADD PRIMARY KEY (`comment_pk`),
  ADD KEY `comments_post_fk` (`comment_post_fk`);

--
-- Indexes for table `follows`
--
ALTER TABLE `follows`
  ADD PRIMARY KEY (`follow_follower_fk`,`follow_followed_fk`),
  ADD KEY `follow_followed_fk` (`follow_followed_fk`);

--
-- Indexes for table `likes`
--
ALTER TABLE `likes`
  ADD PRIMARY KEY (`like_user_fk`,`like_post_fk`),
  ADD KEY `like_post_fk` (`like_post_fk`);

--
-- Indexes for table `posts`
--
ALTER TABLE `posts`
  ADD PRIMARY KEY (`post_pk`),
  ADD UNIQUE KEY `post_pk` (`post_pk`);

--
-- Indexes for table `trends`
--
ALTER TABLE `trends`
  ADD UNIQUE KEY `trend_pk` (`trend_pk`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`user_pk`),
  ADD UNIQUE KEY `user_pk` (`user_pk`),
  ADD UNIQUE KEY `user_email` (`user_email`),
  ADD UNIQUE KEY `user_name` (`user_username`);

--
-- Constraints for dumped tables
--

--
-- Constraints for table `bookmarks`
--
ALTER TABLE `bookmarks`
  ADD CONSTRAINT `bookmarks_ibfk_1` FOREIGN KEY (`bookmark_user_fk`) REFERENCES `users` (`user_pk`) ON DELETE CASCADE,
  ADD CONSTRAINT `bookmarks_ibfk_2` FOREIGN KEY (`bookmark_post_fk`) REFERENCES `posts` (`post_pk`) ON DELETE CASCADE;

--
-- Constraints for table `comments`
--
ALTER TABLE `comments`
  ADD CONSTRAINT `comments_post_fk` FOREIGN KEY (`comment_post_fk`) REFERENCES `posts` (`post_pk`) ON DELETE CASCADE;

--
-- Constraints for table `follows`
--
ALTER TABLE `follows`
  ADD CONSTRAINT `follows_ibfk_1` FOREIGN KEY (`follow_follower_fk`) REFERENCES `users` (`user_pk`) ON DELETE CASCADE,
  ADD CONSTRAINT `follows_ibfk_2` FOREIGN KEY (`follow_followed_fk`) REFERENCES `users` (`user_pk`) ON DELETE CASCADE;

--
-- Constraints for table `likes`
--
ALTER TABLE `likes`
  ADD CONSTRAINT `likes_ibfk_1` FOREIGN KEY (`like_user_fk`) REFERENCES `users` (`user_pk`) ON DELETE CASCADE,
  ADD CONSTRAINT `likes_ibfk_2` FOREIGN KEY (`like_post_fk`) REFERENCES `posts` (`post_pk`) ON DELETE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
