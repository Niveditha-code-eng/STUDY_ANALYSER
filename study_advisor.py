"""
STUDY ADVISOR
What this program does:
  1. Connects to MySQL
  2. Reads the timetable, study log and marks
  3. Decides for each subject:
        - Is the timetable suitable?
        - Does the student need MORE STUDY TIME or MORE FOCUS?
"""

import mysql.connector

DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = "magic"
DB_NAME = "study_db"

GOOD_MARKS = 75        
MIN_HOURS_PER_WEEK = 4  
MIN_FOCUS = 6 

def run_query(cursor, sql):
    """Run one SQL query and return the rows as a list."""
    cursor.execute(sql)
    return cursor.fetchall()


def load_data():
    """Read the 3 tables and combine them into one dictionary.

    The result looks like this:
    {
      ('Anu', 'Maths'): {'planned': 3.0, 'hours': 2.5, 'focus': 4.5, 'weeks': 1, 'marks': 42.0},
      ('Anu', 'Physics'): {...},
    }
    The key is (student, subject) so each subject of each student has its own info.
    """
    connection = mysql.connector.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME
    )
    cursor = connection.cursor()

    data = {}

    rows = run_query(cursor, """
        SELECT student_name, subject, SUM(hours_planned)
        FROM timetable
        GROUP BY student_name, subject
    """)
    for student, subject, planned in rows:
        data[(student, subject)] = {"planned": float(planned), "hours": 0.0,
                                    "focus": 0.0, "weeks": 1, "marks": 0.0}

    
    rows = run_query(cursor, """
        SELECT student_name, subject, SUM(hours_studied), AVG(focus_rating),
               COUNT(DISTINCT YEARWEEK(study_data, 1))
        FROM study_log
        GROUP BY student_name, subject
    """)
    for student, subject, hours, focus, weeks in rows:
        entry = data.setdefault((student, subject),
                                {"planned": 0.0, "hours": 0.0, "focus": 0.0,
                                 "weeks": 1, "marks": 0.0})
        entry["hours"] = float(hours)
        entry["focus"] = float(focus)
        entry["weeks"] = max(int(weeks), 1)  


    rows = run_query(cursor, """
        SELECT student_name, subject, AVG(marks_obtained / max_marks * 100)
        FROM marks
        GROUP BY student_name, subject
    """)
    for student, subject, percent in rows:
        entry = data.setdefault((student, subject),
                                {"planned": 0.0, "hours": 0.0, "focus": 0.0,
                                 "weeks": 1, "marks": 0.0})
        entry["marks"] = float(percent)

    cursor.close()
    connection.close()
    return data


def check_timetable(planned, hours_per_week):
    """Is the timetable suitable for this subject?"""
    if planned == 0:
        return "Subject is NOT in the timetable. Please add study slots."
    if planned < MIN_HOURS_PER_WEEK:
        return f"Only {planned:.1f} hours/week planned. That is too little."
    if hours_per_week < planned * 0.6:
        return (f"{planned:.1f} hours planned but only {hours_per_week:.1f} studied. "
                "The timetable may be unrealistic (wrong timings?).")
    return "Timetable looks suitable."


def give_advice(marks, hours_per_week, focus):
    """Look at marks, study time and focus, then give advice."""
    marks_good = marks >= GOOD_MARKS
    time_low = hours_per_week < MIN_HOURS_PER_WEEK
    focus_low = focus < MIN_FOCUS

    if marks_good and not time_low and not focus_low:
        return "ON TRACK", "Marks are good. Keep doing what you are doing!"
    if marks_good:
        return "GOOD MARKS BUT RISKY", "Marks are fine, but study time or focus is low."
    if time_low and focus_low:
        return "MORE TIME + MORE FOCUS", "Both are low. Fix focus first, then add more hours."
    if time_low:
        return "NEEDS MORE STUDY TIME", "Focus is fine. Just study more hours."
    if focus_low:
        return "NEEDS MORE FOCUS", "Enough hours, but low focus. Remove distractions, take short breaks."
    return "CHANGE STUDY METHOD", "Time and focus are fine but marks are low. Try practice tests or ask a teacher."


def main():
    data = load_data()

    for (student, subject), info in data.items():
        hours_per_week = info["hours"] / info["weeks"]

        timetable_note = check_timetable(info["planned"], hours_per_week)
        verdict, advice = give_advice(info["marks"], hours_per_week, info["focus"])

        print("-" * 55)
        print(f"{student} - {subject}")
        print(f"  Marks: {info['marks']:.1f}%   Study: {hours_per_week:.1f} h/week   "
              f"Focus: {info['focus']:.1f}/10")
        print(f"  Result    : {verdict}")
        print(f"  Advice    : {advice}")
        print(f"  Timetable : {timetable_note}")


if __name__ == "__main__":
    main()
