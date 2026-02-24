# Spec-Workflow Mode for Team Review

`/team-review --spec <spec-id>` で起動された場合の追加手順。

## Additional Reviewer: Requirements Reviewer

3つの標準レビュアー（Security, Quality, Test）に加え、4つ目のレビュアーを起動:

**Requirements Reviewer**
```
"You are a Requirements Reviewer for: {feature} (spec: {spec-id}).

Validate implementation against formal requirements:
- Read: .spec-workflow/specs/{spec-id}/requirements.md
- Read: .spec-workflow/specs/{spec-id}/design.md
- Read: .spec-workflow/specs/{spec-id}/tasks.md

For each Acceptance Criterion in requirements.md:
- Verify: Is there a test that validates this AC?
- Verify: Does the implementation match the WHEN/THEN/SHALL behavior?
- Verify: Are edge cases from ACs handled?

For each Non-Functional Requirement:
- Code Architecture and Modularity compliance
- Performance constraints met
- Security requirements satisfied
- Reliability measures in place
- Usability standards met

For each finding:
- AC ID or NFR section
- Status: Covered / Partially Covered / Missing
- Evidence: test file or code location
- Gap description if not fully covered

Save report to .claude/docs/research/review-requirements-{feature}.md"
```

## Report Enhancement

Step 3 (Synthesize) で追加の読み込み対象:
- `.claude/docs/research/review-requirements-{feature}.md`

Step 4 (Report) のサマリーに追加:
- 要件カバレッジ: {N}/{M} ACs covered
- NFR コンプライアンス: {status per section}
