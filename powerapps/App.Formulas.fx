// ---------------------------------------------------------------------------
// App > Formulas  (Tree view > App > property dropdown: Formulas). Paste all.
// Named formulas: recalculated automatically, no OnStart needed for these.
// English-locale separators. Data sources required: EntraRequests,
// EntraCatalogApps, EntraCatalogGroups (SharePoint) and Office365Users.
// ---------------------------------------------------------------------------

gTheme = {
    Primary: RGBA(15, 108, 189, 1),
    PrimaryHover: RGBA(17, 94, 163, 1),
    PrimaryLight: RGBA(235, 243, 252, 1),
    TopBar: RGBA(27, 26, 25, 1),
    Bg: RGBA(243, 242, 241, 1),
    Card: RGBA(255, 255, 255, 1),
    Border: RGBA(225, 223, 221, 1),
    Text: RGBA(50, 49, 48, 1),
    Muted: RGBA(96, 94, 92, 1),
    Success: RGBA(16, 124, 16, 1),
    SuccessLight: RGBA(223, 246, 221, 1),
    Danger: RGBA(209, 52, 56, 1),
    DangerLight: RGBA(253, 231, 233, 1),
    Warning: RGBA(152, 111, 11, 1),
    WarningLight: RGBA(255, 244, 206, 1)
};

gMe = { Email: Lower(User().Email), Name: User().FullName };

// The catalog lists store members/owners as ";upn1;upn2;" (userPrincipalName, lower case),
// so match on the UPN; User().Email is the mail address, which can differ from the UPN.
gMeKey = ";" & Lower(Coalesce(Office365Users.MyProfileV2().userPrincipalName, User().Email)) & ";";

gAppCatPattern = "^[A-Z0-9][A-Z0-9-]{2,63}$";
gValuePattern = "^[A-Za-z][A-Za-z0-9._-]{0,119}$";

// Groups the signed-in user belongs to or owns (owning teams and role groups).
// "in" on a multi-line column is not delegable: keep Settings > Data row limit at 2000.
gMyGroups = ShowColumns(
    Filter(EntraCatalogGroups, gMeKey in MemberUpns || gMeKey in OwnerUpns),
    GroupId, Title, AppCatId
);

// Owning-team picker: groups the user is a MEMBER of (ER-02 checks membership of the owning team).
gMyTeams = ShowColumns(
    Filter(EntraCatalogGroups, gMeKey in MemberUpns),
    GroupId, Title, AppCatId
);

// App registrations the user's teams own (team tag) or the user owns directly.
gMyApps = Filter(EntraCatalogApps, gMeKey in TeamMemberUpns || gMeKey in OwnerUpns);

gOperations = Table(
    { Key: "newApp", Title: "App registration", Subtitle: "Register a new application: API, app roles, enterprise app and role groups in one request.", Badge: "Most used" },
    { Key: "exposeApi", Title: "Expose an API", Subtitle: "Set the Application ID URI and publish delegated scopes on an app your team owns.", Badge: "" },
    { Key: "addAppRoles", Title: "App roles", Subtitle: "Add User / Admin or custom app roles, each with the group that will hold it.", Badge: "" },
    { Key: "assignGroups", Title: "Role assignments", Subtitle: "Grant Entra groups an app role so the group owners manage who has access.", Badge: "" },
    { Key: "createSP", Title: "Enterprise application", Subtitle: "Create the service principal for an existing app registration.", Badge: "" },
    { Key: "group", Title: "Security group", Subtitle: "Create a security group you own, stamped with your appCatID.", Badge: "" },
    { Key: "myRequests", Title: "My requests", Subtitle: "Track approvals and see exactly what was created.", Badge: "" }
);

gSteps = Table(
    { Step: 1, Title: "Basics", Hint: "Name, owner team, justification" },
    { Step: 2, Title: "Expose an API & claims", Hint: "App ID URI, scopes, token claims" },
    { Step: 3, Title: "App roles & groups", Hint: "Roles and the groups that hold them" },
    { Step: 4, Title: "Enterprise app & owners", Hint: "Service principal, owners, tags" },
    { Step: 5, Title: "Review + submit", Hint: "Check and send for approval" }
);
