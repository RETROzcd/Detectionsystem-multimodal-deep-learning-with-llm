import os
import json
import logging
from typing import Optional
import pymysql

class DBClient:

    def __init__(self) -> None:
        self.host = os.getenv("MYSQL_HOST", "")
        self.port = int(os.getenv("MYSQL_PORT", ""))
        self.user = os.getenv("MYSQL_USER", "")
        self.password = os.getenv("MYSQL_PASSWORD", "")
        self.database = os.getenv("MYSQL_DB", "")

    def _get_conn(self):
        return pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True,
        )
    def create_task(
        self,
        rule_file_path: str,
        preprocess_data: Optional[dict],
        status: str,
    ) -> int:
        preprocess_text = (
            json.dumps(preprocess_data, ensure_ascii=False)
            if preprocess_data is not None
            else None
        )
        sql = """
        INSERT INTO task (rule_file_path, preprocess_data, status)
        VALUES (%s, %s, %s)
        """
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (rule_file_path, preprocess_text, status))
                task_id = cur.lastrowid
        logging.info("Created task row, id=%s", task_id)
        return int(task_id)

    def create_object_classification_response(
        self,
        task_id: int,
        status: str,
        message: Optional[str],
        reason: Optional[str],
        category: Optional[str],
        features: Optional[dict],
    ) -> int:
        """
        在 object_classification_response 表中新建一条记录。
        """
        features_json = (
            json.dumps(features, ensure_ascii=False) if features is not None else None
        )
        sql = """
        INSERT INTO object_classification_response
        (task_id, status, message, reason, category, features)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        task_id,
                        status,
                        message,
                        reason,
                        category,
                        features_json,
                    ),
                )
                oid = cur.lastrowid
        logging.info("Created object_classification_response row, id=%s", oid)
        return int(oid)

    def upsert_task_ai_category_feature(self, task_id: int, acfd) -> None:
        """
        写入/更新「加工后」的 AI 分类与特性（RedisCategoryAndFeatureData），与 task 一对一。
        """
        toy = list(getattr(acfd, "toy_category", None) or [])
        feat = list(getattr(acfd, "features", None) or [])
        sub_chem = list(
            getattr(acfd, "sub_features_chemical_experiment_kit_with_reactive_substances", None) or []
        )
        sub_bat = list(getattr(acfd, "sub_features_battery_powered_toy", None) or [])
        toy_json = json.dumps(toy, ensure_ascii=False)
        feat_json = json.dumps(feat, ensure_ascii=False)
        sub_chem_json = json.dumps(sub_chem, ensure_ascii=False)
        sub_bat_json = json.dumps(sub_bat, ensure_ascii=False)
        sql = """
        INSERT INTO task_ai_category_feature
        (task_id, toy_category, features, sub_features_chemical_experiment_kit_with_reactive_substances,
         sub_features_battery_powered_toy)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            toy_category = VALUES(toy_category),
            features = VALUES(features),
            sub_features_chemical_experiment_kit_with_reactive_substances = VALUES(sub_features_chemical_experiment_kit_with_reactive_substances),
            sub_features_battery_powered_toy = VALUES(sub_features_battery_powered_toy)
        """
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        task_id,
                        toy_json,
                        feat_json,
                        sub_chem_json,
                        sub_bat_json,
                    ),
                )
        logging.info("Upserted task_ai_category_feature for task_id=%s", task_id)

    # ====== rule & rule_check_* ======

    def upsert_rule_and_get_id(self, rule) -> int:
        """
        将 Rule 对象写入 rule 表，并返回对应 id。
        当前实现按 (chapter, title, check_method) 去重，若已存在则直接返回已存在的 id。
        """
        chapter = getattr(rule, "chapter", "")
        title = getattr(rule, "title", "")
        check_method = getattr(rule, "method", "")
        requirement = getattr(rule, "requirements", "")
        precondition = getattr(rule, "preconditions", "")
        age_range_label = getattr(rule, "age_range_label", "")
        review_content = getattr(rule, "audit_content", "")
        llm_prompt = getattr(rule, "llm_prompt", "")

        with self._get_conn() as conn:
            with conn.cursor() as cur:
                # 先查是否已存在
                select_sql = """
                SELECT id FROM rule
                WHERE chapter = %s AND title = %s AND check_method = %s
                LIMIT 1
                """
                cur.execute(select_sql, (chapter, title, check_method))
                row = cur.fetchone()
                if row and "id" in row:
                    return int(row["id"])

                insert_sql = """
                INSERT INTO rule
                (chapter, title, check_method, requirement, precondition,
                 age_range_label, review_content, llm_prompt)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                cur.execute(
                    insert_sql,
                    (
                        chapter,
                        title,
                        check_method,
                        requirement,
                        precondition,
                        age_range_label,
                        review_content,
                        llm_prompt,
                    ),
                )
                rid = cur.lastrowid
        logging.info("Inserted new rule row, id=%s", rid)
        return int(rid)

    def create_rule_check_response(
        self,
        task_id: int,
        run_status: bool,
        message: Optional[str],
    ) -> int:
        """
        在 rule_check_response 表中新建一条记录，返回 id。
        """
        status_str = "success" if run_status else "failed"
        sql = """
        INSERT INTO rule_check_response (task_id, run_status, message)
        VALUES (%s, %s, %s)
        """
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (task_id, status_str, message))
                rid = cur.lastrowid
        logging.info("Created rule_check_response row, id=%s", rid)
        return int(rid)

    def create_rule_check_result(
        self,
        rule_check_response_id: int,
        rule_id: int,
        check_result,
    ) -> int:
        """
        在 rule_check_result 表中新建一条记录。
        """
        necessity_status = (
            "applicable" if getattr(check_result, "necessity_state", True) else "not_applicable"
        )
        necessity_reason = getattr(check_result, "necessity_reason", "")
        pass_status_bool = getattr(check_result, "pass_status", None)
        if pass_status_bool is None:
            pass_status = "unknown"
        else:
            pass_status = "pass" if pass_status_bool else "fail"
        llm_response = getattr(check_result, "llm_response", "")
        reason = getattr(check_result, "reason", "")
        is_error = 0
        error_reason = ""

        sql = """
        INSERT INTO rule_check_result
        (rule_check_response_id, rule_id, necessity_status, necessity_reason,
         pass_status, llm_response, reason, is_error, error_reason)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        rule_check_response_id,
                        rule_id,
                        necessity_status,
                        necessity_reason,
                        pass_status,
                        llm_response,
                        reason,
                        is_error,
                        error_reason,
                    ),
                )
                rid = cur.lastrowid
        logging.info("Created rule_check_result row, id=%s", rid)
        return int(rid)

    def upsert_audit_task_history(
        self,
        session_hash: str,
        product_filenames: str = "",
        packaging_filenames: str = "",
        description_filenames: str = "",
        supplement: str = "",
        image_tiling_algorithm: str = "",
        ai_model: str = "",
        preconditions_str: str = "",
        age_str: str = "",
    ) -> None:
        """
        按 session_hash 插入或更新一条审核任务概览记录，供历史页展示。
        """
        sql = """
        INSERT INTO audit_task_history
        (session_hash, product_filenames, packaging_filenames, description_filenames,
         supplement, image_tiling_algorithm, ai_model, preconditions_str, age_str)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            product_filenames = VALUES(product_filenames),
            packaging_filenames = VALUES(packaging_filenames),
            description_filenames = VALUES(description_filenames),
            supplement = VALUES(supplement),
            image_tiling_algorithm = VALUES(image_tiling_algorithm),
            ai_model = VALUES(ai_model),
            preconditions_str = VALUES(preconditions_str),
            age_str = VALUES(age_str)
        """
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        session_hash,
                        product_filenames or "",
                        packaging_filenames or "",
                        description_filenames or "",
                        supplement or "",
                        image_tiling_algorithm or "",
                        ai_model or "",
                        preconditions_str or "",
                        age_str or "",
                    ),
                )
        logging.info("Upserted audit_task_history for session_hash=%s", session_hash)

    def list_audit_task_history(self, limit: int = 200):
        """
        查询历史审核任务概览，按创建时间倒序，返回字典列表。
        每项包含: session_hash, product_filenames, packaging_filenames, description_filenames,
                 supplement, image_tiling_algorithm, ai_model, preconditions_str, age_str, created_at
        """
        sql = """
        SELECT session_hash, product_filenames, packaging_filenames, description_filenames,
               supplement, image_tiling_algorithm, ai_model, preconditions_str, age_str, created_at
        FROM audit_task_history
        ORDER BY created_at DESC
        LIMIT %s
        """
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (limit,))
                rows = cur.fetchall()
        return list(rows) if rows else []

