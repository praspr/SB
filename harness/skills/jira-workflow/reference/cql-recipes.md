# CQL Recipes — Confluence (cisco-cxe)

CQL is **not** JQL. Use `searchConfluenceUsingCql` with `cloudId`.

## My pages

```cql
creator = currentUser() AND type = page ORDER BY lastmodified DESC
```

```cql
contributor = currentUser() AND type = page AND lastmodified >= now("-30d")
```

## By title or text

```cql
title ~ "Priority Bugs" AND type = page
```

```cql
text ~ "BAQS" AND type = page
```

## By space

```cql
space = CXENG AND type = page AND lastmodified >= now("-2w")
```

```cql
space.title ~ "Assessments" AND type = page
```

## Recent blog posts

```cql
type = blogpost AND lastmodified >= now("-7d") ORDER BY lastmodified DESC
```

## Local mirror

After reading via `getConfluencePage`, optional save to:

```
/Users/praspr/Documents/code_home/ciq/docs/confluence/{page-id}-{slug}.md
```

Use template: `templates/confluence-page-summary.md`
