"""Hand-written courses so search and the bot run before any scraper works."""

from schema import Course

FIXTURES = [
    Course(
        id="11510-CS132000", school="nthu", semester="11510",
        name_zh="微積分（一）", name_en="Calculus I",
        teachers=["吳貞興"], department="CS", credits=3.0,
        times=["W3-4", "F3-4"], venues=["台達館 104"],
        capacity=60, enrolled=58,
    ),
    Course(
        id="11510-EE203001", school="nthu", semester="11510",
        name_zh="熱力學", name_en="Thermodynamics",
        teachers=["李明"], department="EE", credits=3.0,
        times=["T2-4"], venues=["工程一館 201"],
        capacity=40, enrolled=40,
    ),
    Course(
        id="1131-A901000", school="ncku", semester="1131",
        name_zh="計算機概論", name_en="Introduction to Computer Science",
        teachers=["王小明", "陳大同"], department="A9", credits=2.0,
        times=["W5-6"], venues=["資訊系館 65203"],
        capacity=80, enrolled=31,
    ),
]
