import psycopg
from psycopg import sql
import os
from typing import Union

SCNAME = 'myschema'

# problem 1
def entire_search(CONNECTION: str, table_name: str) -> list:
    with psycopg.connect(CONNECTION) as conn:
        query = sql.SQL("""
                        SELECT *
                        FROM {table_name}
                        """).format(table_name = sql.Identifier(SCNAME, table_name))
        cur = conn.execute(query)
        result = cur.fetchall()
    return result
    
# problem 2
def registration_history(CONNECTION: str, student_id: str) -> Union[list, None]:

    with psycopg.connect(CONNECTION) as conn:
            with conn.cursor() as cur:
                # 학생 존재 여부 확인
                student_check_query = sql.SQL("""
                    SELECT EXISTS (
                        SELECT 1
                        FROM {schema}.students
                        WHERE "STUDENT_ID" = %s
                    )
                """).format(schema=sql.Identifier(SCNAME))

                cur.execute(student_check_query, (student_id,))
                student_exists = cur.fetchone()[0]

                if not student_exists:
                    print(f"Not Exist student with STUDENT ID: {student_id}")
                    return []

                # 수강 기록 및 성적 조회
                history_query = sql.SQL("""
                    SELECT 
                        c."YEAR" AS lecture_year,
                        c."SEMESTER" AS lecture_semester,
                        c."COURSE_ID_PREFIX" AS major_code,
                        c."COURSE_ID_NO" AS course_number,
                        c."DIVISION_NO" AS class_id,
                        c."COURSE_NAME" AS course_name,
                        f."NAME" AS professor_name,
                        g."GRADE" AS grade
                    FROM 
                        {schema}.course_registration cr
                    JOIN 
                        {schema}.course c ON cr."COURSE_ID" = c."COURSE_ID"
                    JOIN 
                        {schema}.faculty f ON c."PROF_ID" = f."ID"
                    JOIN 
                        {schema}.grade g ON cr."COURSE_ID" = g."COURSE_ID" 
                        AND cr."STUDENT_ID" = g."STUDENT_ID"
                    WHERE 
                        cr."STUDENT_ID" = %s
                    ORDER BY 
                        c."YEAR" ASC,
                        c."SEMESTER" ASC,
                        c."COURSE_NAME" ASC
                """).format(schema=sql.Identifier(SCNAME))

                cur.execute(history_query, (student_id,))
                result = cur.fetchall()
                return result

# problem 3
def registration(CONNECTION: str, course_id: int, student_id: str) -> Union[list, None]:

    with psycopg.connect(CONNECTION) as conn:
            with conn.cursor() as cur:
                # 강의 존재 여부 확인
                course_check_query = sql.SQL("""
                    SELECT EXISTS (
                        SELECT 1
                        FROM {schema}.course
                        WHERE "COURSE_ID" = %s
                    )
                """).format(schema=sql.Identifier(SCNAME))

                cur.execute(course_check_query, (course_id,))
                course_exists = cur.fetchone()[0]

                if not course_exists:
                    print(f"Not Exist course with COURSE ID: {course_id}")
                    return []

                # 학생 존재 여부 확인
                student_check_query = sql.SQL("""
                    SELECT "NAME"
                    FROM {schema}.students
                    WHERE "STUDENT_ID" = %s
                """).format(schema=sql.Identifier(SCNAME))

                cur.execute(student_check_query, (student_id,))
                student_info = cur.fetchone()

                if not student_info:
                    print(f"Not Exist student with STUDENT ID: {student_id}")
                    return []

                student_name = student_info[0]

                # 중복 수강 신청 여부 확인
                duplication_check_query = sql.SQL("""
                    SELECT c."COURSE_NAME"
                    FROM {schema}.course_registration cr
                    JOIN {schema}.course c ON cr."COURSE_ID" = c."COURSE_ID"
                    WHERE cr."COURSE_ID" = %s AND cr."STUDENT_ID" = %s
                """).format(schema=sql.Identifier(SCNAME))

                cur.execute(duplication_check_query, (course_id, student_id))
                duplication_result = cur.fetchone()

                if duplication_result:
                    course_name = duplication_result[0]
                    print(f"{student_name} is already registrated in {course_name} ({course_id})")
                    return []

                # 수강 신청 삽입
                insert_query = sql.SQL("""
                    INSERT INTO {schema}.course_registration ("COURSE_ID", "STUDENT_ID")
                    VALUES (%s, %s)
                """).format(schema=sql.Identifier(SCNAME))

                cur.execute(insert_query, (course_id, student_id))
                conn.commit()

                # 변경된 테이블 반환
                fetch_all_query = sql.SQL("""
                    SELECT *
                    FROM {schema}.course_registration
                """).format(schema=sql.Identifier(SCNAME))

                cur.execute(fetch_all_query)
                result = cur.fetchall()
                return result


# problem 4
def withdrawal_registration(CONNECTION: str, course_id: int, student_id: str) -> Union[list, None]:

    with psycopg.connect(CONNECTION) as conn:
            with conn.cursor() as cur:
                # 강의 존재 여부 확인
                course_check_query = sql.SQL("""
                    SELECT EXISTS (
                        SELECT 1
                        FROM {schema}.course
                        WHERE "COURSE_ID" = %s
                    )
                """).format(schema=sql.Identifier(SCNAME))

                cur.execute(course_check_query, (course_id,))
                course_exists = cur.fetchone()[0]

                if not course_exists:
                    print(f"Not Exist course with COURSE ID: {course_id}")
                    return []

                # 학생 존재 여부 확인
                student_check_query = sql.SQL("""
                    SELECT "NAME"
                    FROM {schema}.students
                    WHERE "STUDENT_ID" = %s
                """).format(schema=sql.Identifier(SCNAME))

                cur.execute(student_check_query, (student_id,))
                student_info = cur.fetchone()

                if not student_info:
                    print(f"Not Exist student with STUDENT ID: {student_id}")
                    return []

                student_name = student_info[0]

                # 등록 여부 확인
                registration_check_query = sql.SQL("""
                    SELECT c."COURSE_NAME"
                    FROM {schema}.course_registration cr
                    JOIN {schema}.course c ON cr."COURSE_ID" = c."COURSE_ID"
                    WHERE cr."COURSE_ID" = %s AND cr."STUDENT_ID" = %s
                """).format(schema=sql.Identifier(SCNAME))

                cur.execute(registration_check_query, (course_id, student_id))
                registration_result = cur.fetchone()

                if not registration_result:
                    print(f"{student_name} is not registrated in {course_id}")
                    return []

                course_name = registration_result[0]

                # 수강 철회
                delete_query = sql.SQL("""
                    DELETE FROM {schema}.course_registration
                    WHERE "COURSE_ID" = %s AND "STUDENT_ID" = %s
                """).format(schema=sql.Identifier(SCNAME))

                cur.execute(delete_query, (course_id, student_id))
                conn.commit()

                # 변경된 테이블 반환
                fetch_all_query = sql.SQL("""
                    SELECT *
                    FROM {schema}.course_registration
                """).format(schema=sql.Identifier(SCNAME))

                cur.execute(fetch_all_query)
                result = cur.fetchall()
                return result


# problem 5
def modify_lectureroom(CONNECTION: str, course_id: int, buildno: str, roomno: str) -> Union[list, None]:
    
    with psycopg.connect(CONNECTION) as conn:
            with conn.cursor() as cur:
                # 강의 존재 여부 확인
                course_check_query = sql.SQL("""
                    SELECT EXISTS (
                        SELECT 1
                        FROM {schema}.course
                        WHERE "COURSE_ID" = %s
                    )
                """).format(schema=sql.Identifier(SCNAME))

                cur.execute(course_check_query, (course_id,))
                course_exists = cur.fetchone()[0]

                if not course_exists:
                    print(f"Not Exist course with COURSE ID: {course_id}")
                    return []

                # 강의실 존재 여부 확인
                lectureroom_check_query = sql.SQL("""
                    SELECT EXISTS (
                        SELECT 1
                        FROM {schema}.lectureroom
                        WHERE "BUILDNO" = %s AND "ROOMNO" = %s
                    )
                """).format(schema=sql.Identifier(SCNAME))

                cur.execute(lectureroom_check_query, (buildno, roomno))
                lectureroom_exists = cur.fetchone()[0]

                if not lectureroom_exists:
                    print(f"Not Exist lecture room with BUILD NO: {buildno} / ROOM NO: {roomno}")
                    return []

                # 강의실 정보 업데이트
                update_query = sql.SQL("""
                    UPDATE {schema}.course
                    SET "BUILDNO" = %s, "ROOMNO" = %s
                    WHERE "COURSE_ID" = %s
                """).format(schema=sql.Identifier(SCNAME))

                cur.execute(update_query, (buildno, roomno, course_id))
                conn.commit()

                # 변경된 테이블 반환
                fetch_all_query = sql.SQL("""
                    SELECT *
                    FROM {schema}.course
                """).format(schema=sql.Identifier(SCNAME))

                cur.execute(fetch_all_query)
                result = cur.fetchall()
                return result


# sql file execute ( Not Edit )
def execute_sql(CONNECTION, path):
    folder_path = '/'.join(path.split('/')[:-1])
    file = path.split('/')[-1]
    if file in os.listdir(folder_path):
        with psycopg.connect(CONNECTION) as conn:
            conn.execute(open(path, 'r', encoding='utf-8').read())
            conn.commit()
        print("{} EXECUTRED!".format(file))
    else:
        print("{} File Not Exist in {}".format(file, folder_path))
