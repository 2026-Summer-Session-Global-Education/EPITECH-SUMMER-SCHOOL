from render_demo_pdfs import build_pdf, render_for_qa


DOCUMENTS = [
    {
        "filename": "01_Hackathon_Announcement",
        "kicker": "EVENT ANNOUNCEMENT",
        "title": "2026 Youth Cyber Safety Hackathon",
        "subtitle": "Official event announcement from the Future Digital Safety Institute",
        "meta": [
            ("Organizer", "Future Digital Safety Institute"),
            ("Event", "2026 Youth Cyber Safety Hackathon"),
            ("Date", "August 20, 2026, 09:00-18:00"),
            ("Venue", "Hanbit Startup Center, 3rd Floor"),
        ],
        "sections": [
            (
                "Purpose",
                [
                    "The Future Digital Safety Institute will host the 2026 Youth Cyber Safety Hackathon so that students can solve practical security problems through teamwork.",
                    "Each team will select one challenge: phishing detection, secure authentication, or privacy protection, and build a working prototype.",
                ],
            ),
            (
                "Participation and Deliverables",
                [
                    "Teams of two to four high school or university students may apply by August 5, 2026.",
                    "Every team must submit a problem statement, a working prototype, and a five-minute presentation. The top team will receive the Future Digital Safety Institute Award.",
                    "This announcement is the primary event definition referenced by the participation request, training plan, mentoring guide, and results report.",
                ],
            ),
        ],
    },
    {
        "filename": "02_Hackathon_Participation_Request",
        "kicker": "COOPERATION REQUEST",
        "title": "Request for Hackathon Participation",
        "subtitle": "Student nomination request for schools and universities",
        "meta": [
            ("Sender", "Future Digital Safety Institute"),
            ("Recipients", "High schools and universities"),
            ("Related Event", "2026 Youth Cyber Safety Hackathon"),
            ("Nomination Deadline", "August 5, 2026"),
        ],
        "sections": [
            (
                "Requested Action",
                [
                    "The Future Digital Safety Institute requests student nominations for the 2026 Youth Cyber Safety Hackathon.",
                    "Nominated students must form teams of two to four and choose a phishing detection, secure authentication, or privacy protection challenge.",
                ],
            ),
            (
                "Participation Process",
                [
                    "A school coordinator must submit the application and privacy consent form by August 5, 2026.",
                    "Selected teams will attend the main event at Hanbit Startup Center on August 20, 2026.",
                    "This document is a cooperation request for the event defined in 01_Hackathon_Announcement.pdf.",
                ],
            ),
        ],
    },
    {
        "filename": "03_PreHackathon_Training_Plan",
        "kicker": "TRAINING PLAN",
        "title": "Pre-Hackathon Security Training Plan",
        "subtitle": "A mandatory preparation course for the main event",
        "meta": [
            ("Operator", "Future Digital Safety Institute"),
            ("Audience", "2026 Youth Cyber Safety Hackathon teams"),
            ("Training Date", "August 13, 2026"),
            ("Format", "Online practical workshop"),
        ],
        "sections": [
            (
                "Learning Objective",
                [
                    "This training is a mandatory prerequisite for teams entering the 2026 Youth Cyber Safety Hackathon.",
                    "Future Digital Safety Institute instructors will teach threat modeling, secure authentication design, and data minimization through practical exercises.",
                ],
            ),
            (
                "Dependency on the Main Event",
                [
                    "The threat model produced during training is a required input for the problem statement submitted at the main event.",
                    "Only teams that complete the pre-hackathon training may participate in the final hackathon on August 20, 2026.",
                    "This training plan is a prerequisite for the event defined in 01_Hackathon_Announcement.pdf.",
                ],
            ),
        ],
    },
    {
        "filename": "04_Onsite_Mentoring_Guide",
        "kicker": "OPERATIONS GUIDE",
        "title": "Onsite Hackathon Mentoring Guide",
        "subtitle": "Companion material for mentors supporting participant teams",
        "meta": [
            ("Publisher", "Future Digital Safety Institute"),
            ("Applicable Event", "2026 Youth Cyber Safety Hackathon"),
            ("Effective Date", "August 20, 2026"),
            ("Audience", "Technical mentors and event staff"),
        ],
        "sections": [
            (
                "Mentor Role",
                [
                    "This guide is companion material for technical mentors supporting teams at the 2026 Youth Cyber Safety Hackathon.",
                    "Mentors must not provide complete solutions. They should help teams apply the threat models created during pre-hackathon training to prototype design.",
                ],
            ),
            (
                "Review Criteria",
                [
                    "Mentors will review problem clarity, data minimization, authentication failure handling, and demonstration readiness.",
                    "Interim feedback will be reported to the Future Digital Safety Institute operations desk and will not directly determine the final score.",
                    "This mentoring guide is companion material for 03_PreHackathon_Training_Plan.pdf and the event defined in 01_Hackathon_Announcement.pdf.",
                ],
            ),
        ],
    },
    {
        "filename": "05_Hackathon_Results_Report",
        "kicker": "RESULTS REPORT",
        "title": "2026 Youth Cyber Safety Hackathon Results",
        "subtitle": "Event outcomes and follow-up actions",
        "meta": [
            ("Organizer", "Future Digital Safety Institute"),
            ("Event", "2026 Youth Cyber Safety Hackathon"),
            ("Event Date", "August 20, 2026"),
            ("Participation", "18 teams, 62 students"),
        ],
        "sections": [
            (
                "Key Results",
                [
                    "The Future Digital Safety Institute completed the 2026 Youth Cyber Safety Hackathon at Hanbit Startup Center on August 20, 2026.",
                    "Eighteen teams presented phishing detection, secure authentication, and privacy protection prototypes. Every team submitted a problem statement and demonstration video.",
                ],
            ),
            (
                "Follow-Up",
                [
                    "The winning phishing detection prototype will continue in the Future Digital Safety Institute follow-up mentoring program beginning in September 2026.",
                    "The operations team concluded that pre-hackathon training and onsite mentoring improved prototype quality.",
                    "This results report is a continuation of the event announced in 01_Hackathon_Announcement.pdf.",
                ],
            ),
        ],
    },
    {
        "filename": "06_Coastal_Ecology_Survey_Plan",
        "kicker": "UNRELATED CONTROL DOCUMENT",
        "title": "Blue Bay Seagrass Ecology Survey Plan",
        "subtitle": "An independent control sample with no hackathon relationship",
        "meta": [
            ("Organization", "Blue Bay Marine Ecology Center"),
            ("Survey", "2026 Seasonal Seagrass Survey"),
            ("Period", "April-October 2026"),
            ("Location", "Eastern Blue Bay Coast"),
        ],
        "sections": [
            (
                "Survey Purpose",
                [
                    "The Blue Bay Marine Ecology Center will measure seasonal changes in seagrass coverage and juvenile fish density.",
                    "The survey team will repeatedly record water temperature, salinity, underwater visibility, and seagrass coverage at fixed sites.",
                ],
            ),
            (
                "Survey Method",
                [
                    "Divers will photograph a fixed fifty-meter transect and register sample images in the vegetation analysis system.",
                    "The results will support coastal restoration priorities and have no relationship to cybersecurity events or education programs.",
                ],
            ),
        ],
    },
]


if __name__ == "__main__":
    for spec in DOCUMENTS:
        pdf_path = build_pdf(spec)
        png_path = render_for_qa(pdf_path)
        print(f"{pdf_path}\t{png_path}")
