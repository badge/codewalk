# codewalk's syntax

Everything codewalk reads is CommonMark (with tables and strikethrough) and YAML front
matter. It adds no syntax that changes how Markdown parses: every addition is a fenced
block's info string, a link's scheme, text inside a paragraph, or a line in a paragraph or
a blockquote. A file means the same to any Markdown renderer, and reads well in one.

This is the grammar, in EBNF, of what's added. `TEXT` is any characters but newline.

## Names

```ebnf
name        = [ "crate::" ] , segment , { "::" , segment }      (* a tail of a qualified name *)
            | "impl " , [ path , " for " ] , path               (* an impl block *)
            | file , "#" , name ;                               (* a name in a file; any tail of its path *)
path        = segment , { "::" , segment } ;
segment     = ( letter | "_" ) , { letter | digit | "_" } ;
file        = { TEXT - "#" } ;

id          = lower , { lower | digit | "." | "-" } ;           (* requirements, terms, facts *)
lower       = "a" … "z" ;
```

A name resolves if exactly one symbol's qualified name ends with it on `::` boundaries.
`crate::` anchors it at the root. Requirement, term and fact IDs are case-sensitive.

## References in prose

```ebnf
wiki        = "[[" , [ "?" ] , target , [ "|" , label ] , "]]" ;
target      = name
            | "r:" , id                                         (* a requirement *)
            | "t:" , id                                         (* a term *)
            | "f:" , id ;                                       (* a fact *)
label       = { TEXT - "]" } ;

link        = "[" , label , "](" , scheme , ":" , ( name | id ) , ")" ;
scheme      = "walk" | "req" | "term" | "fact" ;

cite        = "`" , id , "`" ;          (* a requirement's ID in backticks, if it's a requirement *)
```

`?` marks a name that may not exist yet: proposed, not an error.

A term is also linked wherever its words appear in prose (its ID with spaces for
hyphens, singular or plural, any case): the first time in each paragraph, not in
headings or links.

## Blocks

```ebnf
walk        = "```walk" , NL , { walk-line , NL } , "```" ;
walk-line   = blank | "//" , TEXT
            | ( name | "r:" , id ) , [ " > " , focus ] , [ " sig" ] ;
focus       = TEXT ;                    (* the first line of the symbol containing it starts the part shown *)

proposal    = "```walk proposed" , [ " " , lang ] , NL , name , NL , { TEXT , NL } , "```" ;
settled     = "```walk settled" , [ " " , lang ] , NL , walk-line , NL , { TEXT , NL } , "```" ;
                                        (* a proposal, written: the code shown, the draft kept *)
lang        = letter , { letter | digit } ;
```

## Definitions

Each is a paragraph whose first line is the marker alone, the text following:

```ebnf
requirement = "r[" , id , "]" , NL , text ;                     (* tracey's; codewalk only reads them *)
term        = "t[" , id , "]" , NL , text ;
fact        = "f[" , id , "]" , [ " " , status ] , NL , text ;
status      = "documented" | "observed" | "assumed" ;            (* assumed if left out *)
```

## Notes

A blockquote whose paragraphs open with a kind is a thread:

```ebnf
thread      = quote-note , { quote-blank , ( quote-note | replies ) } ;
replies     = nested quote-notes, one level deeper ("> > "), replying to the note above them ;
quote-note  = "> " , "[!" , kind , "]" , [ " @" , author , [ ":" ] ] , " " , TEXT , NL , { "> " , TEXT , NL } ;
kind        = "question" | "answer" | "decision" | "note"
            | "request" | "done" ;                               (* any case *)
author      = ( letter | digit | "_" | "." | "-" ) , { letter | digit | "_" | "." | "-" } ;
```

A paragraph in a thread without a kind carries on the note above it. A thread is open
while any question in it, at any depth, has no answer or decision after it (at its own
level, or in its replies). A request stands until a `done` does the same.

A settled thread can be resolved into the changelog: a `## Changelog` section at the
end, one list item a thread, newest first.

## Front matter

```yaml
---
title: …          # else the first heading
summary: …        # else the first paragraph
tags: [a, b]      # or one, as a string
related: [path]   # other codewalks, from this file
kind: prd         # a PRD: a change proposed in full, settled as it's made
---
```

Other keys are left alone.

## Code

In the code, codewalk reads tracey's markers in comments, `// r[impl id]` and
`// r[verify id]` (or `#` in Python), to show a requirement's code.
