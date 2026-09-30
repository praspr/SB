# JQL Recipes — cisco-cxe

Base URL for issues: `https://cisco-cxe.atlassian.net/browse/{KEY}`

## My work

```jql
assignee = currentUser() ORDER BY updated DESC
```

```jql
assignee = currentUser() AND status NOT IN (Done, Closed, Cancelled) ORDER BY updated DESC
```

```jql
reporter = currentUser() ORDER BY updated DESC
```

## By key or project

```jql
key = CXP-47564
```

```jql
project = CXP AND status = Open ORDER BY updated DESC
```

```jql
project = CXPL AND status != Closed ORDER BY priority DESC
```

## Epics and parents

```jql
parent = CXP-31951 ORDER BY rank
```

```jql
"Epic Link" = CXP-31951
```

## Sprint (adjust sprint name/id)

```jql
project = CXP AND sprint in openSprints() AND assignee = currentUser()
```

## Recent activity

```jql
project = CXP AND updated >= -7d ORDER BY updated DESC
```

## Labels

```jql
project = CXP AND labels = "Q1FY27-EC-Assessments-App-Priority-Bugs-tracker"
```

## Pagination

- Use `maxResults: 100` and `nextPageToken` from response
- Never assume a single page contains all results
