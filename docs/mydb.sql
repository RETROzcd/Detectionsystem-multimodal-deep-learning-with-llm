-- 1. 创建数据库
DROP DATABASE IF EXISTS intelligent_detection;
CREATE DATABASE intelligent_detection
DEFAULT CHARACTER SET utf8mb4
DEFAULT COLLATE utf8mb4_unicode_ci;
USE intelligent_detection;

-- 2. 任务表 task
CREATE TABLE task (
    id                INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '任务ID，主键',
    rule_file_path    VARCHAR(255) NOT NULL COMMENT '规则文件存储路径',
    preprocess_data   TEXT NULL COMMENT '预处理相关数据(JSON)',
    status            VARCHAR(32) NOT NULL DEFAULT 'pending' COMMENT '任务状态 pending/running/finished/failed',
    created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    INDEX idx_task_status (status)
) ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4
COMMENT='任务表';


-- 3. 分类特征表 classification_feature
CREATE TABLE classification_feature (
    id            INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '分类特征ID',
    task_id       INT UNSIGNED NOT NULL COMMENT '任务ID',
    data_type     VARCHAR(50) NOT NULL COMMENT '数据类型 image/text/metadata',
    feature_type  VARCHAR(50) NOT NULL COMMENT '特征类型 toy_category/product_feature',
    feature_name  VARCHAR(100) NOT NULL COMMENT '特征名称',
    created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_cf_task (task_id),
    INDEX idx_cf_type (feature_type),
    CONSTRAINT fk_cf_task
        FOREIGN KEY (task_id)
        REFERENCES task(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4
COMMENT='分类特征表';


-- 4. 图片表 image
CREATE TABLE image (
    id                    INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '图片ID',
    task_id               INT UNSIGNED NOT NULL COMMENT '任务ID',
    image_type            VARCHAR(50) NOT NULL COMMENT '图片类型 product/packaging/manual',
    original_path         VARCHAR(255) NOT NULL COMMENT '原始图片路径',
    processed_path        VARCHAR(255) NULL COMMENT '预处理后图片路径',
    segmented_paths       JSON NULL COMMENT '切割图片JSON列表',
    created_at            DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at            DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_image_task (task_id),
    INDEX idx_image_type (image_type),
    CONSTRAINT fk_image_task
        FOREIGN KEY (task_id)
        REFERENCES task(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4
COMMENT='图片表';



-- 5. 对象分类响应表 object_classification_response
CREATE TABLE object_classification_response (
    id             INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '对象分类响应ID',
    task_id        INT UNSIGNED NOT NULL COMMENT '任务ID',
    status         VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT '状态 pending/success/failed',
    message        TEXT NULL COMMENT '响应信息',
    reason         TEXT NULL COMMENT '判断原因',
    category       VARCHAR(100) NULL COMMENT '分类类别',
    features       JSON NULL COMMENT '产品特性JSON',
    created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_ocr_task (task_id),
    INDEX idx_ocr_status (status),
    CONSTRAINT fk_ocr_task
        FOREIGN KEY (task_id)
        REFERENCES task(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE

) ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4
COMMENT='对象分类响应表';


-- 5b. AI 分类加工结果表 task_ai_category_feature
CREATE TABLE task_ai_category_feature (
    id                INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
    task_id           INT UNSIGNED NOT NULL COMMENT '关联 task.id',
    toy_category      JSON NULL COMMENT '加工后玩具类别列表',
    features          JSON NULL COMMENT '加工后产品特性列表',
    sub_features_chemical_experiment_kit_with_reactive_substances JSON NULL COMMENT '化学实验套装相关细分',
    sub_features_battery_powered_toy JSON NULL COMMENT '电池驱动玩具相关细分',
    created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_task_ai_cat (task_id),
    CONSTRAINT fk_tacf_task
        FOREIGN KEY (task_id)
        REFERENCES task(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4
COMMENT='AI 分类加工结果（Redis ai_category_and_feature_data 落库）';


-- 6. 规则检查响应表 rule_check_response
CREATE TABLE rule_check_response (
    id             INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '规则检查响应ID',
    task_id        INT UNSIGNED NOT NULL COMMENT '任务ID',
    run_status     VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT '状态 pending/running/success/failed',
    message        TEXT NULL COMMENT '检查消息',
    created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_rcr_task (task_id),
    INDEX idx_rcr_status (run_status),
    CONSTRAINT fk_rcr_task
        FOREIGN KEY (task_id)
        REFERENCES task(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4
COMMENT='规则检查响应表';


-- 7. 规则表 rule
CREATE TABLE rule (
    id                 INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '规则ID',
    chapter            VARCHAR(50) NOT NULL COMMENT '章节',
    title              VARCHAR(200) NOT NULL COMMENT '规则标题',
    check_method       VARCHAR(100) NOT NULL COMMENT '检查方式 VLM/LLM/manual',
    requirement        TEXT NOT NULL COMMENT '规则要求',
    precondition       JSON NULL COMMENT '规则前置条件',
    age_range_label    VARCHAR(50) NULL COMMENT '适用年龄',
    review_content     TEXT NULL COMMENT '审核内容',
    llm_prompt         TEXT NULL COMMENT 'LLM Prompt',
    created_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_rule_chapter (chapter),
    INDEX idx_rule_age (age_range_label)
) ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4
COMMENT='规则表';


-- 8. 规则检查结果表 rule_check_result
CREATE TABLE rule_check_result (
    id                      INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '检查结果ID',
    rule_check_response_id  INT UNSIGNED NOT NULL COMMENT '规则检查响应ID',
    rule_id                 INT UNSIGNED NOT NULL COMMENT '规则ID',
    necessity_status        VARCHAR(20) NOT NULL COMMENT '规则是否适用 applicable/not_applicable',
    necessity_reason        TEXT NULL COMMENT '适用原因',
    pass_status             VARCHAR(20) NOT NULL COMMENT '通过状态 pass/fail/unknown',
    llm_response            TEXT NULL COMMENT 'LLM原始响应',
    reason                  TEXT NULL COMMENT '检查结果原因',
    is_error                TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否存在错误',
    error_reason            TEXT NULL COMMENT '错误原因',
    created_at              DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_rcrr_response (rule_check_response_id),
    INDEX idx_rcrr_rule (rule_id),
    INDEX idx_rcrr_pass_status (pass_status),
    CONSTRAINT fk_rcrr_response
        FOREIGN KEY (rule_check_response_id)
        REFERENCES rule_check_response(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_rcrr_rule
        FOREIGN KEY (rule_id)
        REFERENCES rule(id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
) ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4
COMMENT='规则检查结果表';

-- 9. 历史审核任务概览表 audit_task_history
CREATE TABLE audit_task_history (
    id                     BIGINT NOT NULL AUTO_INCREMENT COMMENT '自增主键',
    session_hash            VARCHAR(64) NOT NULL COMMENT '会话/任务唯一标识',
    product_filenames       TEXT NULL COMMENT '产品文件名列表（文本/JSON均可）',
    packaging_filenames     TEXT NULL COMMENT '包装文件名列表（文本/JSON均可）',
    description_filenames   TEXT NULL COMMENT '说明书文件名列表（文本/JSON均可）',
    supplement              TEXT NULL COMMENT '补充说明',
    image_tiling_algorithm  VARCHAR(128) NULL COMMENT '图片拼接/切图算法标识',
    ai_model                VARCHAR(128) NULL COMMENT '使用的AI模型标识',
    preconditions_str       TEXT NULL COMMENT '前置条件序列化字符串',
    age_str                 VARCHAR(256) NULL COMMENT '年龄范围字符串',
    created_at              DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at              DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_session_hash (session_hash)
) ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4
COMMENT='历史审核任务概览表';
