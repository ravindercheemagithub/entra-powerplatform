# HTTP action bodies (flow ER-02)

Paste each file's contents into the **Body** of the HTTP action with the same name.
`@{...}` are Power Automate expressions; the classic designer turns them into
expression tokens on paste. If your designer keeps them as plain text, switch the
flow to the classic designer (toggle **New designer** off), paste, then switch back.

Action names matter: expressions reference other actions by name
(`body('HTTP_Create_application')`). Rename each action exactly as in
docs/04-POWER-AUTOMATE.md (spaces become underscores in expressions).

Group creation and app owners are not part of this platform: groups are created elsewhere and
added with "Add existing group" (flow ER-04); app registrations get no owners. The enterprise
application is created from the new app registration's appId (`HTTP_Create_SP.json`); Entra sets
its servicePrincipalType to `Application` automatically (the property is read-only in Graph).
