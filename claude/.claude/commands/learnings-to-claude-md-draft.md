# /learnings-to-claude-md

Extract learnings from the current conversation and create a draft CLAUDE.md addition file.

## What it does

Analyzes the entire conversation to identify:
- User's working style and preferences
- Communication patterns and expectations
- Technical approaches that worked well
- Problem-solving strategies used
- Debugging and logging preferences
- Code organization standards

Creates a draft file with timestamp: `CLAUDE-draft-YYYY-MM-DD_HHMMSS.md`

## Usage

```
/learnings-to-claude-md
```

## Analysis Focus Areas

### Working Style
- Iterative development patterns
- Problem escalation strategies
- Persistence and retry approaches

### Technical Patterns
- Code organization preferences
- Error handling strategies
- Debugging approaches
- Testing and verification methods

### Communication
- Preferred output formats
- Use of visual indicators
- Level of detail expected
- Progress reporting style

### Tool Development
- General-purpose vs specific solutions
- CLI design patterns
- Logging strategies
- Documentation standards

## Output Format

The generated file will contain:
1. Core principles extracted from the conversation
2. Specific technical patterns observed
3. Communication style preferences
4. Code examples and templates
5. Key phrases and indicators (like "ultrathink")

## Example Output Structure

```markdown
# CLAUDE.md Additions - [Session Topic] - YYYY-MM-DD

## Core Principles
[Extracted principles]

## Technical Standards
[Code patterns and standards]

## Communication Style
[Preferred formats and indicators]

## Patterns to Follow
[Specific examples from session]
```

## Implementation Notes

When analyzing the conversation:
- Focus on user messages for style preferences
- Look for iterations and what improved between attempts
- Note specific feedback on what worked/didn't work
- Extract concrete examples over abstract principles
- Identify tools and libraries the user prefers