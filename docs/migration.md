# Repository migration

The working directory was retained so the existing local Codex conversation continues to address the same project path. A full private sibling backup of the old workspace was made and its source files were compared byte-for-byte before replacement.

The new repository has independent history: an initial teacher-template snapshot, followed by the glove tooling/course integration. The original scratch repository had no commits or remote. No Codex session database was edited.

Private original course references (Teams PDF and class roster) are retained under ignored `.local/course-reference/` and in the backup. They are absent from Git, including the public history.

The project is temporarily `PRJ-PENDING-GestureGlove`. The supplied roster lists ST033 (Mykhailo Sichkaruk) and ST029 (Yaroslav Marochok), with empty ProjectID fields. The two individual sections are ready for their respective authors. A GitHub invitation has not been sent.

See `template-provenance.md` for the upstream revision and course links, `development.md` for setup, and `validation.md` for checks and limitations.
