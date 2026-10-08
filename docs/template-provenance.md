# Template provenance and course references

Initialized as an independent repository from [2026_sthdf_class_template](https://github.com/06-STH-Projects/2026_sthdf_class_template), commit `d30dd1dfe166e97d95ad7ffca26d84ca73fa2b64`, on 2026-10-08.
The first commit contains the original tracked template files; upstream history is not imported.
This follows the teacher's [clean-clone guide](https://knifes.systemthinking.sk/en/knifes/K000119-clean-clone-of-a-class-repository/).
The original README is retained in `course-template.md`; obsolete automation is retained as `.txt` reference files.

Preserve LICENSE, LICENSE-DOCS and attribution. Individual template pages may specify additional/different licenses in frontmatter; retain those notices. The Adafruit Fritzing part has its own license.

Current [course site](https://sthdf-2026.systemthinking.sk/). Required naming: `PRJ-YYY-ProjectName` and `ST-XXX-Name`. `PENDING` in this repository explicitly means unassigned, not a real course identifier.

The template includes seven student sections: About Me, Knowledge Contribution (KNIFE), Project Summary, Project Outcomes, Pitch Presentation, Final Presentation, Reflexia.
Each student must document their own contribution. A team repository is not proof that individual submission requirements have been satisfied.

The clean-clone guide describes teacher import of repositories, while the course homepage also describes PR submissions. Confirm the current hand-in procedure and deadlines with the teacher before submitting. We have not submitted anything to the teacher.

The private Teams/course PDF includes meeting access details and is intentionally absent from Git. Public links above preserve the useful repository guidance.

Migration corrections: Makefile uses Bash from PATH; `flake.lock` is explicitly tracked; Docusaurus navigation follows existing directories; the case-sensitive `7Ds` link and obsolete student-deliverable links were corrected in both the instance and generator template. Obsolete MkDocs/release automation was replaced with a Docusaurus build-and-artifact workflow.
