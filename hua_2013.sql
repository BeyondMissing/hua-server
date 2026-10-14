/*
 Navicat Premium Data Transfer

 Source Server         : localhost
 Source Server Type    : MySQL
 Source Server Version : 80021
 Source Host           : localhost:3306
 Source Schema         : hua_2013

 Target Server Type    : MySQL
 Target Server Version : 80021
 File Encoding         : 65001

 Date: 14/10/2026 13:43:34
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for accounts
-- ----------------------------
DROP TABLE IF EXISTS `accounts`;
CREATE TABLE `accounts`  (
  `user_id` int UNSIGNED NOT NULL COMMENT '米米号',
  `login_name` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '昵称',
  `password_hash` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '密码 md5(md5())',
  `role_created` int NOT NULL DEFAULT 0 COMMENT '已创建角色',
  `banned` int NOT NULL COMMENT '已封禁',
  `enable_friends_application` int NOT NULL DEFAULT 1 COMMENT '允许添加好友',
  PRIMARY KEY (`user_id`) USING BTREE,
  UNIQUE INDEX `unique_login_name`(`login_name` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for game_servers
-- ----------------------------
DROP TABLE IF EXISTS `game_servers`;
CREATE TABLE `game_servers`  (
  `id` int UNSIGNED NOT NULL,
  `user_rate` int UNSIGNED NOT NULL DEFAULT 0,
  `ip` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `port` int UNSIGNED NOT NULL,
  `friends` int UNSIGNED NOT NULL DEFAULT 0,
  `enabled` tinyint UNSIGNED NOT NULL DEFAULT 1,
  `server_num` int UNSIGNED NOT NULL DEFAULT 1,
  `vip` tinyint UNSIGNED NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for medal_event_progress
-- ----------------------------
DROP TABLE IF EXISTS `medal_event_progress`;
CREATE TABLE `medal_event_progress`  (
  `user_id` int UNSIGNED NOT NULL,
  `event_id` int UNSIGNED NOT NULL,
  `progress` int UNSIGNED NOT NULL DEFAULT 0,
  PRIMARY KEY (`user_id`, `event_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for player_beauty_profiles
-- ----------------------------
DROP TABLE IF EXISTS `player_beauty_profiles`;
CREATE TABLE `player_beauty_profiles`  (
  `user_id` bigint UNSIGNED NOT NULL,
  `user_nation` int UNSIGNED NOT NULL DEFAULT 1,
  `user_nick` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT '',
  `user_words` varchar(120) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT '',
  `user_rank_num` int UNSIGNED NOT NULL DEFAULT 9999,
  `user_vote` int UNSIGNED NOT NULL DEFAULT 0,
  `user_fan` int UNSIGNED NOT NULL DEFAULT 0,
  `user_color` int UNSIGNED NOT NULL DEFAULT 0,
  `skin` int UNSIGNED NOT NULL DEFAULT 0,
  `user_face` int UNSIGNED NOT NULL DEFAULT 0,
  `user_eye` int UNSIGNED NOT NULL DEFAULT 0,
  `user_eyebrow` int UNSIGNED NOT NULL DEFAULT 0,
  `user_lip` int UNSIGNED NOT NULL DEFAULT 0,
  `clothes_json` json NULL,
  `recent_presents_json` json NULL,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`user_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for player_clothes
-- ----------------------------
DROP TABLE IF EXISTS `player_clothes`;
CREATE TABLE `player_clothes`  (
  `user_id` int UNSIGNED NOT NULL,
  `cloth_id` int UNSIGNED NOT NULL,
  `acquired_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`user_id`, `cloth_id`) USING BTREE,
  CONSTRAINT `fk_player_clothes_account` FOREIGN KEY (`user_id`) REFERENCES `accounts` (`user_id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for player_completed_tasks
-- ----------------------------
DROP TABLE IF EXISTS `player_completed_tasks`;
CREATE TABLE `player_completed_tasks`  (
  `user_id` int UNSIGNED NOT NULL,
  `job_id` int UNSIGNED NOT NULL,
  `completed_at` int UNSIGNED NOT NULL DEFAULT 0,
  PRIMARY KEY (`user_id`, `job_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for player_ext_info
-- ----------------------------
DROP TABLE IF EXISTS `player_ext_info`;
CREATE TABLE `player_ext_info`  (
  `user_id` int UNSIGNED NOT NULL,
  `cloth_pk_rank_idx` int UNSIGNED NOT NULL DEFAULT 0,
  `patrol_title` int UNSIGNED NOT NULL DEFAULT 0,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`user_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for player_flowers
-- ----------------------------
DROP TABLE IF EXISTS `player_flowers`;
CREATE TABLE `player_flowers`  (
  `user_id` int UNSIGNED NOT NULL,
  `item_id` int UNSIGNED NOT NULL,
  `amount` int UNSIGNED NOT NULL DEFAULT 0,
  PRIMARY KEY (`user_id`, `item_id`) USING BTREE,
  INDEX `ix_player_flowers_item`(`item_id` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for player_friends
-- ----------------------------
DROP TABLE IF EXISTS `player_friends`;
CREATE TABLE `player_friends`  (
  `owner_user_id` int NOT NULL,
  `friend_user_id` int NOT NULL,
  `status` int NOT NULL,
  `application_time` int UNSIGNED NULL DEFAULT NULL,
  `added_time` int UNSIGNED NULL DEFAULT NULL,
  `last_contact_time` int UNSIGNED NULL DEFAULT NULL,
  PRIMARY KEY (`owner_user_id`, `friend_user_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for player_home_goods
-- ----------------------------
DROP TABLE IF EXISTS `player_home_goods`;
CREATE TABLE `player_home_goods`  (
  `user_id` int UNSIGNED NOT NULL,
  `slot_index` int UNSIGNED NOT NULL,
  `item_id` int UNSIGNED NOT NULL,
  `x` int UNSIGNED NOT NULL DEFAULT 0,
  `y` int UNSIGNED NOT NULL DEFAULT 0,
  `state` int UNSIGNED NOT NULL DEFAULT 0,
  `reserved_1` int UNSIGNED NOT NULL DEFAULT 0,
  `reserved_2` int UNSIGNED NOT NULL DEFAULT 0,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_set` int UNSIGNED NOT NULL DEFAULT 0,
  PRIMARY KEY (`user_id`, `slot_index`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for player_home_houses
-- ----------------------------
DROP TABLE IF EXISTS `player_home_houses`;
CREATE TABLE `player_home_houses`  (
  `user_id` int UNSIGNED NOT NULL,
  `slot_index` int UNSIGNED NOT NULL,
  `item_id` int UNSIGNED NOT NULL,
  `x` int UNSIGNED NOT NULL DEFAULT 0,
  `y` int UNSIGNED NOT NULL DEFAULT 0,
  `open_flag` int UNSIGNED NOT NULL DEFAULT 0,
  `reserved` int UNSIGNED NOT NULL DEFAULT 0,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`user_id`, `slot_index`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for player_home_plants
-- ----------------------------
DROP TABLE IF EXISTS `player_home_plants`;
CREATE TABLE `player_home_plants`  (
  `user_id` int UNSIGNED NOT NULL,
  `plot_no` int UNSIGNED NOT NULL,
  `plant_id` int UNSIGNED NOT NULL DEFAULT 0,
  `magic_id` int UNSIGNED NOT NULL DEFAULT 0,
  `state` tinyint UNSIGNED NOT NULL DEFAULT 0,
  `level` tinyint UNSIGNED NOT NULL DEFAULT 0,
  `experience` int UNSIGNED NOT NULL DEFAULT 0,
  `quality` tinyint UNSIGNED NOT NULL DEFAULT 0,
  `pollen_id` int UNSIGNED NOT NULL DEFAULT 0,
  `pollen_count` tinyint UNSIGNED NOT NULL DEFAULT 0,
  `flower_id` int UNSIGNED NOT NULL DEFAULT 0,
  `flower_count` tinyint UNSIGNED NOT NULL DEFAULT 0,
  `dust_count` tinyint UNSIGNED NOT NULL DEFAULT 0,
  `seed_count` tinyint UNSIGNED NOT NULL DEFAULT 0,
  `tool_state` int UNSIGNED NOT NULL DEFAULT 0,
  `tool_time` int UNSIGNED NOT NULL DEFAULT 0,
  `pot_id` int UNSIGNED NOT NULL DEFAULT 0,
  `pollen_type` int UNSIGNED NOT NULL DEFAULT 0,
  `nutrient` int UNSIGNED NOT NULL DEFAULT 0,
  `moisture` int UNSIGNED NOT NULL DEFAULT 0,
  `x` int UNSIGNED NOT NULL DEFAULT 0,
  `y` int UNSIGNED NOT NULL DEFAULT 0,
  `owner_id` int UNSIGNED NOT NULL DEFAULT 0,
  `next_state` tinyint UNSIGNED NOT NULL DEFAULT 0,
  `next_level` tinyint UNSIGNED NOT NULL DEFAULT 0,
  `next_time` int UNSIGNED NOT NULL DEFAULT 0,
  `grass` int UNSIGNED NOT NULL DEFAULT 0,
  `item_use_flag` tinyint UNSIGNED NOT NULL DEFAULT 0,
  `add_flower_flag` int UNSIGNED NOT NULL DEFAULT 0,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`user_id`, `plot_no`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for player_home_props
-- ----------------------------
DROP TABLE IF EXISTS `player_home_props`;
CREATE TABLE `player_home_props`  (
  `user_id` int UNSIGNED NOT NULL,
  `item_id` int UNSIGNED NOT NULL,
  `amount` int UNSIGNED NOT NULL DEFAULT 0,
  PRIMARY KEY (`user_id`, `item_id`) USING BTREE,
  INDEX `ix_player_home_props_item`(`item_id` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for player_homes
-- ----------------------------
DROP TABLE IF EXISTS `player_homes`;
CREATE TABLE `player_homes`  (
  `user_id` int UNSIGNED NOT NULL,
  `charm` int UNSIGNED NOT NULL DEFAULT 0,
  `plant_exp` int UNSIGNED NOT NULL DEFAULT 0,
  `background_id` int UNSIGNED NOT NULL DEFAULT 1000003,
  `vip_level` int UNSIGNED NOT NULL DEFAULT 0,
  `pet_level` int UNSIGNED NOT NULL DEFAULT 0,
  `home_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT '',
  `weather` tinyint UNSIGNED NOT NULL DEFAULT 0 COMMENT '1=小雨 2=中雨 6=晴 7=阴 8=彩虹',
  `temperature` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT '',
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`user_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for player_house_goods
-- ----------------------------
DROP TABLE IF EXISTS `player_house_goods`;
CREATE TABLE `player_house_goods`  (
  `user_id` int UNSIGNED NOT NULL,
  `item_id` int UNSIGNED NOT NULL,
  `no` int UNSIGNED NOT NULL,
  `x` int UNSIGNED NOT NULL DEFAULT 0,
  `y` int UNSIGNED NOT NULL DEFAULT 0,
  `m` int UNSIGNED NOT NULL DEFAULT 0,
  `z` int UNSIGNED NOT NULL DEFAULT 0,
  `is_set` tinyint(1) NOT NULL DEFAULT 0,
  PRIMARY KEY (`user_id`, `no`) USING BTREE,
  INDEX `idx_player_house_goods_user`(`user_id` ASC) USING BTREE,
  INDEX `idx_player_house_goods_item`(`item_id` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for player_houses
-- ----------------------------
DROP TABLE IF EXISTS `player_houses`;
CREATE TABLE `player_houses`  (
  `user_id` bigint UNSIGNED NOT NULL,
  `house_id` int UNSIGNED NOT NULL,
  PRIMARY KEY (`user_id`, `house_id`) USING BTREE,
  INDEX `idx_player_actions_action_id`(`house_id` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for player_magics
-- ----------------------------
DROP TABLE IF EXISTS `player_magics`;
CREATE TABLE `player_magics`  (
  `user_id` bigint UNSIGNED NOT NULL,
  `action_id` int UNSIGNED NOT NULL,
  `amount` int UNSIGNED NOT NULL DEFAULT 1,
  PRIMARY KEY (`user_id`, `action_id`) USING BTREE,
  INDEX `idx_player_actions_action_id`(`action_id` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for player_materials
-- ----------------------------
DROP TABLE IF EXISTS `player_materials`;
CREATE TABLE `player_materials`  (
  `user_id` int UNSIGNED NOT NULL,
  `item_id` int UNSIGNED NOT NULL,
  `amount` int UNSIGNED NOT NULL DEFAULT 0,
  PRIMARY KEY (`user_id`, `item_id`) USING BTREE,
  INDEX `ix_play_materials_item`(`item_id` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for player_medals
-- ----------------------------
DROP TABLE IF EXISTS `player_medals`;
CREATE TABLE `player_medals`  (
  `user_id` int UNSIGNED NOT NULL,
  `medal_id` int UNSIGNED NOT NULL,
  `value_bits` int UNSIGNED NOT NULL DEFAULT 0,
  `get_time` int UNSIGNED NOT NULL DEFAULT 0,
  `show_flag` int UNSIGNED NOT NULL DEFAULT 0,
  PRIMARY KEY (`user_id`, `medal_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for player_once_flags
-- ----------------------------
DROP TABLE IF EXISTS `player_once_flags`;
CREATE TABLE `player_once_flags`  (
  `user_id` int UNSIGNED NOT NULL,
  `flag_id` int UNSIGNED NOT NULL,
  `flag_value` tinyint UNSIGNED NOT NULL DEFAULT 1,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`user_id`, `flag_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for player_pet_letters
-- ----------------------------
DROP TABLE IF EXISTS `player_pet_letters`;
CREATE TABLE `player_pet_letters`  (
  `id` bigint UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id` bigint UNSIGNED NOT NULL,
  `pet_id` bigint UNSIGNED NOT NULL DEFAULT 0,
  `task_id` int UNSIGNED NOT NULL,
  `step` int UNSIGNED NOT NULL DEFAULT 1,
  `status` int UNSIGNED NOT NULL DEFAULT 0,
  `process` int UNSIGNED NOT NULL DEFAULT 0,
  `letter_time` int UNSIGNED NOT NULL DEFAULT 0,
  `total_process` int UNSIGNED NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_player_pet_letters_user`(`user_id` ASC, `pet_id` ASC, `letter_time` ASC) USING BTREE,
  INDEX `idx_player_pet_letters_task`(`user_id` ASC, `task_id` ASC, `step` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for player_pet_replies
-- ----------------------------
DROP TABLE IF EXISTS `player_pet_replies`;
CREATE TABLE `player_pet_replies`  (
  `id` bigint UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id` bigint UNSIGNED NOT NULL,
  `pet_id` bigint UNSIGNED NOT NULL DEFAULT 0,
  `mail_id` int UNSIGNED NOT NULL,
  `mail_type` int UNSIGNED NOT NULL DEFAULT 1,
  `send_time` int UNSIGNED NOT NULL DEFAULT 0,
  `state` int UNSIGNED NOT NULL DEFAULT 0,
  `reply_time` int UNSIGNED NOT NULL DEFAULT 0,
  `content` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_player_pet_replies_user`(`user_id` ASC, `pet_id` ASC, `mail_type` ASC, `send_time` ASC) USING BTREE,
  INDEX `idx_player_pet_replies_mail`(`user_id` ASC, `pet_id` ASC, `mail_id` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 5 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for player_pet_supplies
-- ----------------------------
DROP TABLE IF EXISTS `player_pet_supplies`;
CREATE TABLE `player_pet_supplies`  (
  `user_id` int UNSIGNED NOT NULL,
  `item_id` int NOT NULL,
  `amount` int UNSIGNED NOT NULL,
  PRIMARY KEY (`user_id`, `item_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for player_pets
-- ----------------------------
DROP TABLE IF EXISTS `player_pets`;
CREATE TABLE `player_pets`  (
  `user_id` int UNSIGNED NOT NULL,
  `pet_id` int UNSIGNED NOT NULL,
  `age` int UNSIGNED NOT NULL DEFAULT 0,
  `love_energy` int UNSIGNED NOT NULL DEFAULT 0,
  `nickname` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT '',
  `hungry_index` int UNSIGNED NOT NULL DEFAULT 100000,
  `clean_index` int UNSIGNED NOT NULL DEFAULT 100000,
  `mood_index` int UNSIGNED NOT NULL DEFAULT 100000,
  `health_state` int UNSIGNED NOT NULL DEFAULT 0,
  `is_vip` tinyint UNSIGNED NOT NULL DEFAULT 0,
  `wonderful_value` int UNSIGNED NOT NULL DEFAULT 0,
  `skills_json` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL,
  `rest_at` tinyint UNSIGNED NOT NULL DEFAULT 0 COMMENT '0=follow, 1=home, 2=house',
  PRIMARY KEY (`user_id`) USING BTREE,
  INDEX `idx_player_pets_user`(`user_id` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for player_pollens
-- ----------------------------
DROP TABLE IF EXISTS `player_pollens`;
CREATE TABLE `player_pollens`  (
  `user_id` int UNSIGNED NOT NULL,
  `pollen_id` int UNSIGNED NOT NULL,
  `amount` int UNSIGNED NOT NULL DEFAULT 0,
  PRIMARY KEY (`user_id`, `pollen_id`) USING BTREE,
  INDEX `ix_player_seeds_item`(`pollen_id` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for player_pots
-- ----------------------------
DROP TABLE IF EXISTS `player_pots`;
CREATE TABLE `player_pots`  (
  `user_id` int UNSIGNED NOT NULL,
  `item_id` int UNSIGNED NOT NULL,
  `amount` int UNSIGNED NOT NULL DEFAULT 0,
  PRIMARY KEY (`user_id`, `item_id`) USING BTREE,
  INDEX `ix_player_seeds_item`(`item_id` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for player_profiles
-- ----------------------------
DROP TABLE IF EXISTS `player_profiles`;
CREATE TABLE `player_profiles`  (
  `user_id` int UNSIGNED NOT NULL,
  `nickname` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT '',
  `map_id` int UNSIGNED NOT NULL DEFAULT 1,
  `map_x` int UNSIGNED NOT NULL DEFAULT 600,
  `map_y` int UNSIGNED NOT NULL DEFAULT 330,
  `new_user_job` int UNSIGNED NOT NULL DEFAULT 11,
  `login_time` int UNSIGNED NOT NULL DEFAULT 0,
  `reg_time` int UNSIGNED NOT NULL DEFAULT 0,
  `birthday` int UNSIGNED NOT NULL DEFAULT 1,
  `nationality` int UNSIGNED NOT NULL DEFAULT 1,
  `love` int UNSIGNED NOT NULL DEFAULT 0,
  `beautiful` int UNSIGNED NOT NULL DEFAULT 0,
  `wisdom` int UNSIGNED NOT NULL DEFAULT 0,
  `plant_grade` int UNSIGNED NOT NULL DEFAULT 1,
  `faerie_grade` int UNSIGNED NOT NULL DEFAULT 1,
  `login_count` int UNSIGNED NOT NULL DEFAULT 0,
  `online_time_all` int UNSIGNED NOT NULL DEFAULT 0,
  `login_last` int UNSIGNED NOT NULL DEFAULT 0,
  `online_time_today` int UNSIGNED NOT NULL DEFAULT 0,
  `money` int UNSIGNED NOT NULL DEFAULT 0,
  `faerie_follow_id` int UNSIGNED NOT NULL DEFAULT 0,
  `face_color` int UNSIGNED NOT NULL DEFAULT 0,
  `face` int UNSIGNED NOT NULL DEFAULT 0,
  `eye` int UNSIGNED NOT NULL DEFAULT 0,
  `eyebrow` int UNSIGNED NOT NULL DEFAULT 0,
  `lip` int UNSIGNED NOT NULL DEFAULT 0,
  `title_id` int UNSIGNED NOT NULL DEFAULT 0,
  `vip_level` int UNSIGNED NOT NULL DEFAULT 0,
  `vip_end_time` int UNSIGNED NOT NULL DEFAULT 0,
  `friend_flag` int UNSIGNED NOT NULL DEFAULT 0,
  `clothing_json` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`user_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for player_puppets
-- ----------------------------
DROP TABLE IF EXISTS `player_puppets`;
CREATE TABLE `player_puppets`  (
  `user_id` int UNSIGNED NOT NULL,
  `puppet_id` int UNSIGNED NOT NULL DEFAULT 0,
  `follow_flag` tinyint UNSIGNED NOT NULL DEFAULT 0,
  `rest_tech_point` int UNSIGNED NOT NULL DEFAULT 0,
  `flower_num` int UNSIGNED NOT NULL DEFAULT 0,
  `love_value` int UNSIGNED NOT NULL DEFAULT 0,
  `kind_value` int UNSIGNED NOT NULL DEFAULT 0,
  `evil_value` int UNSIGNED NOT NULL DEFAULT 0,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`user_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for player_seeds
-- ----------------------------
DROP TABLE IF EXISTS `player_seeds`;
CREATE TABLE `player_seeds`  (
  `user_id` int UNSIGNED NOT NULL,
  `item_id` int UNSIGNED NOT NULL,
  `amount` int UNSIGNED NOT NULL DEFAULT 0,
  PRIMARY KEY (`user_id`, `item_id`) USING BTREE,
  INDEX `ix_player_seeds_item`(`item_id` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for player_suitings
-- ----------------------------
DROP TABLE IF EXISTS `player_suitings`;
CREATE TABLE `player_suitings`  (
  `user_id` int UNSIGNED NOT NULL,
  `slot_index` int UNSIGNED NOT NULL,
  `tool_id` int UNSIGNED NOT NULL DEFAULT 0,
  `headdress_id` int UNSIGNED NOT NULL DEFAULT 0,
  `mask_id` int UNSIGNED NOT NULL DEFAULT 0,
  `hair_id` int UNSIGNED NOT NULL DEFAULT 0,
  `earring_id` int UNSIGNED NOT NULL DEFAULT 0,
  `necklace_id` int UNSIGNED NOT NULL DEFAULT 0,
  `belt_id` int UNSIGNED NOT NULL DEFAULT 0,
  `cloth_id` int UNSIGNED NOT NULL DEFAULT 0,
  `bangle_id` int UNSIGNED NOT NULL DEFAULT 0,
  `shoes_id` int UNSIGNED NOT NULL DEFAULT 0,
  `anklet_id` int UNSIGNED NOT NULL DEFAULT 0,
  `skirt_id` int UNSIGNED NOT NULL DEFAULT 0,
  `wing_id` int UNSIGNED NOT NULL DEFAULT 0,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`user_id`, `slot_index`) USING BTREE,
  CONSTRAINT `fk_player_suitings_account` FOREIGN KEY (`user_id`) REFERENCES `accounts` (`user_id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for player_synthetic_daily
-- ----------------------------
DROP TABLE IF EXISTS `player_synthetic_daily`;
CREATE TABLE `player_synthetic_daily`  (
  `user_id` int UNSIGNED NOT NULL,
  `game_id` int UNSIGNED NOT NULL,
  `award_date` date NOT NULL,
  `award_count` int UNSIGNED NOT NULL DEFAULT 0,
  PRIMARY KEY (`user_id`, `game_id`, `award_date`) USING BTREE,
  CONSTRAINT `player_synthetic_daily_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `accounts` (`user_id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for player_synthetic_items
-- ----------------------------
DROP TABLE IF EXISTS `player_synthetic_items`;
CREATE TABLE `player_synthetic_items`  (
  `user_id` int UNSIGNED NOT NULL,
  `item_id` int UNSIGNED NOT NULL,
  `play_count` int UNSIGNED NOT NULL DEFAULT 0,
  `score_total` bigint UNSIGNED NOT NULL DEFAULT 0,
  `score_highest` int UNSIGNED NOT NULL DEFAULT 0,
  `made_count` int UNSIGNED NOT NULL DEFAULT 0,
  `last_score` int UNSIGNED NOT NULL DEFAULT 0,
  `last_mode` int UNSIGNED NOT NULL DEFAULT 0,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`user_id`, `item_id`) USING BTREE,
  CONSTRAINT `player_synthetic_items_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `accounts` (`user_id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for player_synthetic_progress
-- ----------------------------
DROP TABLE IF EXISTS `player_synthetic_progress`;
CREATE TABLE `player_synthetic_progress`  (
  `user_id` int UNSIGNED NOT NULL,
  `game_id` int UNSIGNED NOT NULL,
  `goods_index` int UNSIGNED NOT NULL,
  `exp_done` int UNSIGNED NOT NULL DEFAULT 0,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`user_id`, `game_id`, `goods_index`) USING BTREE,
  CONSTRAINT `player_synthetic_progress_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `accounts` (`user_id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for player_synthetic_runs
-- ----------------------------
DROP TABLE IF EXISTS `player_synthetic_runs`;
CREATE TABLE `player_synthetic_runs`  (
  `user_id` int UNSIGNED NOT NULL,
  `item_id` int UNSIGNED NOT NULL,
  `game_mode` int UNSIGNED NOT NULL,
  `session_token` varchar(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  `started_at` bigint UNSIGNED NOT NULL,
  `active` tinyint UNSIGNED NOT NULL DEFAULT 1,
  PRIMARY KEY (`user_id`) USING BTREE,
  CONSTRAINT `player_synthetic_runs_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `accounts` (`user_id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for player_task_items
-- ----------------------------
DROP TABLE IF EXISTS `player_task_items`;
CREATE TABLE `player_task_items`  (
  `user_id` int UNSIGNED NOT NULL,
  `item_type` int UNSIGNED NOT NULL,
  `item_id` int UNSIGNED NOT NULL,
  `amount` int UNSIGNED NOT NULL DEFAULT 0,
  PRIMARY KEY (`user_id`, `item_id`, `item_type`) USING BTREE,
  INDEX `ix_player_task_items_item`(`item_type` ASC, `item_id` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for player_task_progress
-- ----------------------------
DROP TABLE IF EXISTS `player_task_progress`;
CREATE TABLE `player_task_progress`  (
  `user_id` int UNSIGNED NOT NULL,
  `job_id` int UNSIGNED NOT NULL,
  `step` int UNSIGNED NOT NULL DEFAULT 1,
  `flag` int UNSIGNED NOT NULL DEFAULT 0,
  `process` int UNSIGNED NOT NULL DEFAULT 0,
  `total_process` int UNSIGNED NOT NULL DEFAULT 0,
  `get_time` int UNSIGNED NOT NULL DEFAULT 0,
  PRIMARY KEY (`user_id`, `job_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for seed_plant_parameters
-- ----------------------------
DROP TABLE IF EXISTS `seed_plant_parameters`;
CREATE TABLE `seed_plant_parameters`  (
  `id` int NOT NULL,
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `nutrient_max` int NULL DEFAULT NULL,
  `moisture_max` int NULL DEFAULT NULL,
  `quality` int NULL DEFAULT NULL,
  `stage_vals1` decimal(12, 6) NULL DEFAULT NULL,
  `stage_vals2` decimal(12, 6) NULL DEFAULT NULL,
  `stage_vals3` decimal(12, 6) NULL DEFAULT NULL,
  `stage_vals4` decimal(12, 6) NULL DEFAULT NULL,
  `nutrient_leak_val` int NULL DEFAULT NULL,
  `moisture_leak_val` int NULL DEFAULT NULL,
  `sun_moisture_val` int NULL DEFAULT NULL,
  `little_rain_moisture_val` int NULL DEFAULT NULL,
  `mid_rain_moisture_val` int NULL DEFAULT NULL,
  `big_rain_moisture_val` int NULL DEFAULT NULL,
  `little_snow_moisture_val` int NULL DEFAULT NULL,
  `mid_snow_moisture_val` int NULL DEFAULT NULL,
  `big_snow_moisture_val` int NULL DEFAULT NULL,
  `wu_moisture_val` int NULL DEFAULT NULL,
  `caihong_moisture_val` int NULL DEFAULT NULL,
  `sun_moisture_rate` decimal(12, 6) NULL DEFAULT NULL,
  `little_rain_moisture_rate` decimal(12, 6) NULL DEFAULT NULL,
  `mid_rain_moisture_rate` decimal(12, 6) NULL DEFAULT NULL,
  `big_rain_moisture_rate` decimal(12, 6) NULL DEFAULT NULL,
  `little_snow_moisture_rate` decimal(12, 6) NULL DEFAULT NULL,
  `mid_snow_moisture_rate` decimal(12, 6) NULL DEFAULT NULL,
  `big_snow_moisture_rate` decimal(12, 6) NULL DEFAULT NULL,
  `wu_moisture_rate` decimal(12, 6) NULL DEFAULT NULL,
  `caihong_moisture_rate` decimal(12, 6) NULL DEFAULT NULL,
  `sun_nutrient_rate` decimal(12, 6) NULL DEFAULT NULL,
  `little_rain_nutrient_rate` decimal(12, 6) NULL DEFAULT NULL,
  `mid_rain_nutrient_rate` decimal(12, 6) NULL DEFAULT NULL,
  `big_rain_nutrient_rate` decimal(12, 6) NULL DEFAULT NULL,
  `little_snow_nutrient_rate` decimal(12, 6) NULL DEFAULT NULL,
  `mid_snow_nutrient_rate` decimal(12, 6) NULL DEFAULT NULL,
  `big_snow_nutrient_rate` decimal(12, 6) NULL DEFAULT NULL,
  `wu_nutrient_rate` decimal(12, 6) NULL DEFAULT NULL,
  `caihong_nutrient_rate` decimal(12, 6) NULL DEFAULT NULL,
  `sun_grow_rate` decimal(12, 6) NULL DEFAULT NULL,
  `little_rain_grow_rate` decimal(12, 6) NULL DEFAULT NULL,
  `mid_rain_grow_rate` decimal(12, 6) NULL DEFAULT NULL,
  `big_rain_grow_rate` decimal(12, 6) NULL DEFAULT NULL,
  `little_snow_grow_rate` decimal(12, 6) NULL DEFAULT NULL,
  `mid_snow_grow_rate` decimal(12, 6) NULL DEFAULT NULL,
  `big_snow_grow_rate` decimal(12, 6) NULL DEFAULT NULL,
  `wu_grow_rate` decimal(12, 6) NULL DEFAULT NULL,
  `caihong_grow_rate` decimal(12, 6) NULL DEFAULT NULL,
  `nutrient_reduce` decimal(12, 6) NULL DEFAULT NULL,
  `moisture_reduce` decimal(12, 6) NULL DEFAULT NULL,
  `is_like_earth` int NULL DEFAULT NULL,
  `is_in_earth` int NULL DEFAULT NULL,
  `flower_out_put` int NULL DEFAULT NULL,
  `poll_out_put` int NULL DEFAULT NULL,
  `flower_out_put_id_1` int NULL DEFAULT NULL,
  `flower_out_put_id_2` int NULL DEFAULT NULL,
  `poll_out_put_id` int NULL DEFAULT NULL,
  `wilt_day` int NULL DEFAULT NULL,
  `can_poll_id_1` int NULL DEFAULT NULL,
  `can_poll_id_2` int NULL DEFAULT NULL,
  `can_poll_id_3` int NULL DEFAULT NULL,
  `fruit_id_1` int NULL DEFAULT NULL,
  `fruit_id_2` int NULL DEFAULT NULL,
  `fruit_id_3` int NULL DEFAULT NULL,
  `exp_good` int NULL DEFAULT NULL,
  `exp_bad` int NULL DEFAULT NULL,
  `pet_id` int NULL DEFAULT NULL,
  `expect_time` int NULL DEFAULT NULL,
  `HarvestUp` int NULL DEFAULT NULL,
  `energyNeed` int NULL DEFAULT NULL,
  `stage1_time_min_vip0_neutral` decimal(12, 6) NULL DEFAULT NULL,
  `stage2_time_min_vip0_neutral` decimal(12, 6) NULL DEFAULT NULL,
  `stage3_time_min_vip0_neutral` decimal(12, 6) NULL DEFAULT NULL,
  `stage4_time_min_vip0_neutral` decimal(12, 6) NULL DEFAULT NULL,
  `total_time_h_vip0_neutral` decimal(12, 6) NULL DEFAULT NULL,
  `expect_time_delta_h` decimal(12, 6) NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for task_available
-- ----------------------------
DROP TABLE IF EXISTS `task_available`;
CREATE TABLE `task_available`  (
  `main_id` int UNSIGNED NOT NULL,
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `start_npc_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  PRIMARY KEY (`main_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for task_items
-- ----------------------------
DROP TABLE IF EXISTS `task_items`;
CREATE TABLE `task_items`  (
  `ID` int NOT NULL,
  `Name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `Type` int NULL DEFAULT NULL,
  `Task` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `UseFlag` int NULL DEFAULT NULL,
  `GuideID` int NULL DEFAULT NULL,
  `TurnIcon` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `TurnGet` int NULL DEFAULT NULL,
  `Probability` int NULL DEFAULT NULL,
  `OtherIcon` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `mapID` int NULL DEFAULT NULL,
  `initNum` int NULL DEFAULT NULL,
  `IconPosition` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `needTime` int NULL DEFAULT NULL,
  `UseArea` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `Des` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `OtherDes` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  PRIMARY KEY (`ID`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for task_list
-- ----------------------------
DROP TABLE IF EXISTS `task_list`;
CREATE TABLE `task_list`  (
  `main_id` int NOT NULL,
  `type` int NULL DEFAULT NULL,
  `plant_level` int NULL DEFAULT NULL,
  `id` int NOT NULL,
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `start_need` int NULL DEFAULT NULL,
  `req_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `nextreq_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `req_cond` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `vip_level` int NULL DEFAULT NULL,
  `trigger_type` int NULL DEFAULT NULL,
  `lasttime` int NULL DEFAULT NULL,
  `over_type` int NULL DEFAULT NULL,
  `start_npc` int NULL DEFAULT NULL,
  `got_item` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `finish_npc` int NULL DEFAULT NULL,
  `req_item` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `recycle_item` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `need_use_item` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `req_event` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `action` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `plant_seed` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `req_mini_game` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `req_game` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `reward_item_girl` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `reward_item_boy` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `give_item_num` int NULL DEFAULT NULL,
  `reg_date` int NULL DEFAULT NULL,
  `type_change` int NULL DEFAULT NULL,
  PRIMARY KEY (`main_id`, `id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for task_talking
-- ----------------------------
DROP TABLE IF EXISTS `task_talking`;
CREATE TABLE `task_talking`  (
  `main_id` int NOT NULL,
  `id` int NOT NULL,
  `start_npc_before_talk` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `start_npc_after_talk` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `beginjob_tip_talk` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `start_npc_being_talk` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `start_npc_complete_talk` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `finish_npc_before_talk` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `finish_subtask_talk` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `finish_npc_being_talk` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `give_item_talk` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `task_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `task_desc_npcs` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `task_summon` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `task_summon_npcs` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  PRIMARY KEY (`main_id`, `id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for type_activity_icons
-- ----------------------------
DROP TABLE IF EXISTS `type_activity_icons`;
CREATE TABLE `type_activity_icons`  (
  `id` int NOT NULL,
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `hide` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for type_bones
-- ----------------------------
DROP TABLE IF EXISTS `type_bones`;
CREATE TABLE `type_bones`  (
  `id` int NOT NULL,
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `type_num` int NOT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for type_cloth_icons
-- ----------------------------
DROP TABLE IF EXISTS `type_cloth_icons`;
CREATE TABLE `type_cloth_icons`  (
  `id` int NOT NULL,
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `cloth_type` int NULL DEFAULT NULL,
  `type_num` int NULL DEFAULT NULL,
  `equivalent` int NULL DEFAULT NULL,
  `equiv_cnt` int NULL DEFAULT NULL,
  `source` int NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for type_clothes
-- ----------------------------
DROP TABLE IF EXISTS `type_clothes`;
CREATE TABLE `type_clothes`  (
  `id` int NOT NULL,
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `sex` int NULL DEFAULT NULL,
  `cloth_type` int NOT NULL,
  `level` int NULL DEFAULT NULL,
  `vip` int NULL DEFAULT NULL,
  `equivalent` int NULL DEFAULT NULL,
  `style` int NULL DEFAULT NULL,
  `money_type` int NULL DEFAULT NULL,
  `suit` int NULL DEFAULT NULL,
  `vip_level` int NULL DEFAULT NULL,
  `t_type` int NULL DEFAULT NULL,
  `source` int NULL DEFAULT NULL,
  `price` int UNSIGNED NULL DEFAULT NULL,
  `type_num` int UNSIGNED NULL DEFAULT NULL,
  `equiv_cnt` int NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for type_flowers
-- ----------------------------
DROP TABLE IF EXISTS `type_flowers`;
CREATE TABLE `type_flowers`  (
  `id` int NOT NULL,
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `flower_type` int NULL DEFAULT NULL,
  `color_type` int NULL DEFAULT NULL,
  `color_value` int NULL DEFAULT NULL,
  `map` int NULL DEFAULT NULL,
  `des` int NULL DEFAULT NULL,
  `sell` int NULL DEFAULT NULL,
  `hot` int NULL DEFAULT NULL,
  `talk` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for type_home_bg
-- ----------------------------
DROP TABLE IF EXISTS `type_home_bg`;
CREATE TABLE `type_home_bg`  (
  `id` int NOT NULL,
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `event_x` int NULL DEFAULT NULL,
  `event_y` int NULL DEFAULT NULL,
  `vip` int NULL DEFAULT NULL,
  `source` int NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for type_home_goods
-- ----------------------------
DROP TABLE IF EXISTS `type_home_goods`;
CREATE TABLE `type_home_goods`  (
  `id` int NOT NULL,
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `tool_type` int NULL DEFAULT NULL,
  `price` int NULL DEFAULT NULL,
  `max` int NULL DEFAULT NULL,
  `vip` int NULL DEFAULT NULL,
  `source` int NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for type_home_props
-- ----------------------------
DROP TABLE IF EXISTS `type_home_props`;
CREATE TABLE `type_home_props`  (
  `id` int NOT NULL,
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `tips` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `use_for_plant_ids` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `tool_type` int NULL DEFAULT NULL,
  `level` int NULL DEFAULT NULL,
  `allows` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `price` int NULL DEFAULT NULL,
  `times` int NULL DEFAULT NULL,
  `add_water_num` int NULL DEFAULT NULL,
  `add_nutrition_num` int NULL DEFAULT NULL,
  `equivalent` int NULL DEFAULT NULL,
  `equiv_cnt` int NULL DEFAULT NULL,
  `buy_num` int NULL DEFAULT NULL,
  `source` int NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for type_house_goods
-- ----------------------------
DROP TABLE IF EXISTS `type_house_goods`;
CREATE TABLE `type_house_goods`  (
  `id` int NOT NULL,
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `music_type` int NULL DEFAULT NULL,
  `level` int NULL DEFAULT NULL,
  `vip` int NULL DEFAULT NULL,
  `equivalent` int NULL DEFAULT NULL,
  `house_type` int NULL DEFAULT NULL,
  `vip_level` int NULL DEFAULT NULL,
  `source` int NULL DEFAULT NULL,
  `price` int NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for type_houses
-- ----------------------------
DROP TABLE IF EXISTS `type_houses`;
CREATE TABLE `type_houses`  (
  `id` int NOT NULL,
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `level` int NULL DEFAULT NULL,
  `price` int NULL DEFAULT NULL,
  `garden_type` int NULL DEFAULT NULL,
  `equivalent` int NULL DEFAULT NULL,
  `equiv_cnt` int NULL DEFAULT NULL,
  `source` int NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for type_magics
-- ----------------------------
DROP TABLE IF EXISTS `type_magics`;
CREATE TABLE `type_magics`  (
  `id` int NOT NULL,
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for type_materials
-- ----------------------------
DROP TABLE IF EXISTS `type_materials`;
CREATE TABLE `type_materials`  (
  `id` int NOT NULL,
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `price` int NULL DEFAULT NULL,
  `source` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for type_npc_jobs
-- ----------------------------
DROP TABLE IF EXISTS `type_npc_jobs`;
CREATE TABLE `type_npc_jobs`  (
  `npc_id` int UNSIGNED NOT NULL,
  `job_id` int UNSIGNED NOT NULL,
  `step` int UNSIGNED NOT NULL,
  `role_mask` tinyint UNSIGNED NOT NULL DEFAULT 1,
  `job_type` tinyint UNSIGNED NOT NULL DEFAULT 0,
  `step_need` int UNSIGNED NOT NULL DEFAULT 0,
  `start_npc` int UNSIGNED NOT NULL DEFAULT 0,
  `finish_npc` int UNSIGNED NOT NULL DEFAULT 0,
  PRIMARY KEY (`npc_id`, `job_id`, `step`) USING BTREE,
  INDEX `idx_type_npc_jobs_job`(`job_id` ASC, `step` ASC) USING BTREE,
  INDEX `idx_type_npc_jobs_npc`(`npc_id` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for type_npcs
-- ----------------------------
DROP TABLE IF EXISTS `type_npcs`;
CREATE TABLE `type_npcs`  (
  `id` int UNSIGNED NOT NULL,
  `name` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT '',
  `sex` tinyint UNSIGNED NOT NULL DEFAULT 0,
  `map_id` int UNSIGNED NOT NULL DEFAULT 0,
  `init_x` int UNSIGNED NOT NULL DEFAULT 0,
  `init_y` int UNSIGNED NOT NULL DEFAULT 0,
  `face` int UNSIGNED NOT NULL DEFAULT 0,
  `skin` int UNSIGNED NOT NULL DEFAULT 0,
  `eyebrow` int UNSIGNED NOT NULL DEFAULT 0,
  `eye` int UNSIGNED NOT NULL DEFAULT 0,
  `lip` int UNSIGNED NOT NULL DEFAULT 0,
  `tool` int UNSIGNED NOT NULL DEFAULT 0,
  `headdress` int UNSIGNED NOT NULL DEFAULT 0,
  `mask` int UNSIGNED NOT NULL DEFAULT 0,
  `hair` int UNSIGNED NOT NULL DEFAULT 0,
  `earring` int UNSIGNED NOT NULL DEFAULT 0,
  `necklace` int UNSIGNED NOT NULL DEFAULT 0,
  `belt` int UNSIGNED NOT NULL DEFAULT 0,
  `top` int UNSIGNED NOT NULL DEFAULT 0,
  `bangle` int UNSIGNED NOT NULL DEFAULT 0,
  `shoes` int UNSIGNED NOT NULL DEFAULT 0,
  `anklet` int UNSIGNED NOT NULL DEFAULT 0,
  `bottom` int UNSIGNED NOT NULL DEFAULT 0,
  `wing` int UNSIGNED NOT NULL DEFAULT 0,
  `nationality` int UNSIGNED NOT NULL DEFAULT 0,
  `hide` tinyint UNSIGNED NOT NULL DEFAULT 0,
  `org_talk` tinyint UNSIGNED NOT NULL DEFAULT 0,
  `near_width` int UNSIGNED NOT NULL DEFAULT 0,
  `near_height` int UNSIGNED NOT NULL DEFAULT 0,
  `dance_party_topic` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT '',
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_type_npcs_map`(`map_id` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for type_pet_supplies
-- ----------------------------
DROP TABLE IF EXISTS `type_pet_supplies`;
CREATE TABLE `type_pet_supplies`  (
  `id` int NOT NULL,
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `price` int NULL DEFAULT NULL,
  `level` int NULL DEFAULT NULL,
  `grade` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `energy` int NULL DEFAULT NULL,
  `hungry` int NULL DEFAULT NULL,
  `sanitary` int NULL DEFAULT NULL,
  `spirit` int NULL DEFAULT NULL,
  `equivalent` int NULL DEFAULT NULL,
  `equiv_cnt` int NULL DEFAULT NULL,
  `source` int NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for type_pollens
-- ----------------------------
DROP TABLE IF EXISTS `type_pollens`;
CREATE TABLE `type_pollens`  (
  `id` int NOT NULL,
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `area` int NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for type_pots
-- ----------------------------
DROP TABLE IF EXISTS `type_pots`;
CREATE TABLE `type_pots`  (
  `id` int NOT NULL,
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `level` int NULL DEFAULT NULL,
  `price` int NULL DEFAULT NULL,
  `times` int NULL DEFAULT NULL,
  `equivalent` int NULL DEFAULT NULL,
  `equiv_cnt` int NULL DEFAULT NULL,
  `source` int NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for type_seeds
-- ----------------------------
DROP TABLE IF EXISTS `type_seeds`;
CREATE TABLE `type_seeds`  (
  `id` int NOT NULL,
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `level` int NULL DEFAULT NULL,
  `price` int NULL DEFAULT NULL,
  `exp` int NULL DEFAULT NULL,
  `time` int NULL DEFAULT NULL,
  `area` int NULL DEFAULT NULL,
  `source` int NULL DEFAULT NULL,
  `des` int NULL DEFAULT NULL,
  `love_weather` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `talk` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for type_skin_colors
-- ----------------------------
DROP TABLE IF EXISTS `type_skin_colors`;
CREATE TABLE `type_skin_colors`  (
  `id` int NOT NULL,
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Event structure for evt_player_home_plants_growth_1m
-- ----------------------------
DROP EVENT IF EXISTS `evt_player_home_plants_growth_1m`;
delimiter ;;
CREATE EVENT `evt_player_home_plants_growth_1m`
ON SCHEDULE
EVERY '1' MINUTE STARTS '2026-10-05 22:26:22'
ON COMPLETION PRESERVE
DO BEGIN
    
    
    UPDATE `player_home_plants`
       SET `next_time` = CASE WHEN `next_time` > 0 THEN `next_time` - 1 ELSE 0 END
     WHERE `state` IN (1, 3, 4, 6);

    
    
    UPDATE `player_home_plants`
       SET `state` = 2
     WHERE `state` IN (1, 3, 4, 6)
       AND `next_time` = 0
       AND `level` >= 5;

    
    
    UPDATE `player_home_plants` AS p
    JOIN `seed_plant_parameters` AS s ON s.`id` = p.`plant_id`
       SET p.`level` = 2,
           p.`next_level` = 3,
           p.`next_time` = CAST(ROUND(100 / s.`stage_vals2`) AS UNSIGNED)
     WHERE p.`state` IN (1, 3, 4, 6)
       AND p.`next_time` = 0
       AND p.`level` = 1 AND p.`next_level` = 2
       AND s.`stage_vals2` > 0;

    UPDATE `player_home_plants` AS p
    JOIN `seed_plant_parameters` AS s ON s.`id` = p.`plant_id`
       SET p.`level` = 3,
           p.`next_level` = 4,
           p.`next_time` = CAST(ROUND(100 / s.`stage_vals3`) AS UNSIGNED)
     WHERE p.`state` IN (1, 3, 4, 6)
       AND p.`next_time` = 0
       AND p.`level` = 2 AND p.`next_level` = 3
       AND s.`stage_vals3` > 0;

    UPDATE `player_home_plants` AS p
    JOIN `seed_plant_parameters` AS s ON s.`id` = p.`plant_id`
       SET p.`level` = 4,
           p.`next_level` = 5,
           p.`next_time` = CAST(ROUND(100 / s.`stage_vals4`) AS UNSIGNED)
     WHERE p.`state` IN (1, 3, 4, 6)
       AND p.`next_time` = 0
       AND p.`level` = 3 AND p.`next_level` = 4
       AND s.`stage_vals4` > 0;

    UPDATE `player_home_plants` AS p
    JOIN `seed_plant_parameters` AS s ON s.`id` = p.`plant_id`
       SET p.`level` = 5,
           p.`next_level` = 6,
           p.`state` = 6,
           p.`next_state` = 2,
           p.`dust_count` = CASE WHEN COALESCE(s.`poll_out_put`, 0) > 0
                                 THEN s.`poll_out_put` ELSE p.`dust_count` END,
           p.`next_time` = COALESCE(s.`wilt_day`, 0) * 24 * 60
     WHERE p.`state` IN (1, 3, 4, 6)
       AND p.`next_time` = 0
       AND p.`level` = 4 AND p.`next_level` = 5;
END
;;
delimiter ;

-- ----------------------------
-- Event structure for evt_player_home_plants_resources_1h
-- ----------------------------
DROP EVENT IF EXISTS `evt_player_home_plants_resources_1h`;
delimiter ;;
CREATE EVENT `evt_player_home_plants_resources_1h`
ON SCHEDULE
EVERY '1' HOUR STARTS '2026-10-05 23:25:22'
ON COMPLETION PRESERVE
DO BEGIN
    
    
    UPDATE `player_home_plants` AS p
    JOIN `seed_plant_parameters` AS s ON s.`id` = p.`plant_id`
       SET p.`state` = CASE
               WHEN (CASE WHEN p.`nutrient` > 200000
                          THEN p.`nutrient` - 200000 ELSE 0 END) = 0
                AND (CASE WHEN p.`moisture` > 200000
                          THEN p.`moisture` - 200000 ELSE 0 END) = 0
                   THEN 5
               WHEN (CASE WHEN p.`moisture` > 200000
                          THEN p.`moisture` - 200000 ELSE 0 END)
                    < COALESCE(s.`moisture_leak_val`, 0) * 100000
                   THEN 4
               WHEN (CASE WHEN p.`nutrient` > 200000
                          THEN p.`nutrient` - 200000 ELSE 0 END)
                    < COALESCE(s.`nutrient_leak_val`, 0) * 100000
                   THEN 3
               ELSE p.`state`
           END,
           p.`nutrient` = CASE WHEN p.`nutrient` > 200000
                               THEN p.`nutrient` - 200000 ELSE 0 END,
           p.`moisture` = CASE WHEN p.`moisture` > 200000
                               THEN p.`moisture` - 200000 ELSE 0 END
     WHERE p.`plant_id` > 0
       AND p.`state` <> 2;
END
;;
delimiter ;

-- ----------------------------
-- Event structure for evt_player_pets_daily_vip_reward
-- ----------------------------
DROP EVENT IF EXISTS `evt_player_pets_daily_vip_reward`;
delimiter ;;
CREATE EVENT `evt_player_pets_daily_vip_reward`
ON SCHEDULE
EVERY '1' DAY STARTS '2026-10-01 00:00:00'
ON COMPLETION PRESERVE
DO BEGIN
    UPDATE `player_pets`
    SET `wonderful_value` = LEAST(CAST(COALESCE(`wonderful_value`, 0) AS DECIMAL(20, 0)) + 5, 4294967295)
    WHERE `is_vip` = 1;
END
;;
delimiter ;

-- ----------------------------
-- Event structure for evt_player_pets_hourly_decay
-- ----------------------------
DROP EVENT IF EXISTS `evt_player_pets_hourly_decay`;
delimiter ;;
CREATE EVENT `evt_player_pets_hourly_decay`
ON SCHEDULE
EVERY '1' HOUR STARTS '2026-10-01 00:00:00'
ON COMPLETION PRESERVE
DO BEGIN
    UPDATE `player_pets`
    SET
        `hungry_index` = GREATEST(CAST(COALESCE(`hungry_index`, 0) AS SIGNED) - 100000, 0),
        `clean_index` = GREATEST(CAST(COALESCE(`clean_index`, 0) AS SIGNED) - 100000, 0),
        `mood_index` = GREATEST(CAST(COALESCE(`mood_index`, 0) AS SIGNED) - 100000, 0),
        `health_state` = CASE
            WHEN COALESCE(`hungry_index`, 0) = 0
             AND COALESCE(`clean_index`, 0) = 0
             AND COALESCE(`mood_index`, 0) = 0
            THEN 1
            ELSE `health_state`
        END,
        `love_energy` = CASE
            WHEN `is_vip` = 0 AND `health_state` = 1
            THEN GREATEST(CAST(COALESCE(`love_energy`, 0) AS SIGNED) - 1, 0)
            ELSE `love_energy`
        END;
END
;;
delimiter ;

SET FOREIGN_KEY_CHECKS = 1;
