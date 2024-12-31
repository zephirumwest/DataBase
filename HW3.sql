select course_id, title 
from course
where course_id in (select course_id from takes where id = '12345')
