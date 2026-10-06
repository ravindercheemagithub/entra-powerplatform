#!/usr/bin/env python3
"""
Generates the paste-ready screen YAML in ../screens/ from one place, so control
names, theme and layout stay consistent. Run:  python3 build.py

Screens (create them in Studio with exactly these names):
  scrHome        cards for every operation + recent requests
  scrNewApp      "Register an application" wizard: 5 sections, Submit / Next / Cancel
  scrNewGroup    new security group (standalone request, or inline for the wizard)
  scrAppChange   changes to an EXISTING app: expose API, app roles, role assignments, enterprise app
  scrMyRequests  request history with approval stages and results
"""
from __future__ import annotations

from pathlib import Path

from pa import (button, checkbox, combobox, container, dropdown, emit, field_label, frame, gallery, hint, html, icon,
                label, link, q, radio, rect, status_badge, text_input, toggle)

OUT = Path(__file__).resolve().parent.parent / "screens"

COL1_X, COL_W = "0", "(Parent.Width - 24) / 2"
COL2_X = "(Parent.Width + 24) / 2"
NO_TEAM = '{Mode: "", GroupId: "", DisplayName: "", Description: "", OwnerIds: ""}'
NEW_REQ_ID = 'Set(varReqId, "REQ-" & Text(Now(), "yymm") & "-" & Upper(Left(Substitute(Text(GUID()), "-", ""), 6)))'
def clean(expr: str) -> str:
    """Free text the flow embeds in Graph JSON strings: no line breaks, double quotes or backslashes."""
    return f'Substitute(Substitute(Substitute(Substitute(Trim({expr}), Char(13), ""), Char(10), " "), """", "\'"), "\\", "/")'


USERS = "Office365Users.SearchUserV2({searchTerm: Self.SearchText, top: 15, isSearchTermRequired: false}).value"


def root(sfx: str, children: list) -> list:
    return [container(f"cntRoot_{sfx}", 0, 0, "Parent.Width", "Parent.Height", children, fill="gTheme.Bg")]


def write(name: str, nodes: list, header: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.pa.yaml").write_text(f"# {header}\n# Paste into screen {name}: copy all, select the screen in the Tree view, Ctrl+V.\n" + emit(nodes) + "\n")


# ============================================================================ scrHome
def home() -> None:
    s = "Home"
    cards = gallery(
        "galOps_Home", "gOperations", 16, 146, "Parent.Width - 16 - 400", "Parent.Height - 160", 160,
        wrap=3,
        on_select="""Switch(ThisItem.Key,
    "newApp", Set(varResetNewApp, true); Navigate(scrNewApp, ScreenTransition.Fade),
    "group", Set(varGroupMode, "standalone"); Set(varGroupSuggest, "grp-"); Navigate(scrNewGroup, ScreenTransition.Fade),
    "onboardGroup", Navigate(scrAddGroup, ScreenTransition.Fade),
    "myRequests", Set(varSelectedReqId, Blank()); Navigate(scrMyRequests, ScreenTransition.Fade),
    Set(varOp, ThisItem.Key); Set(varResetChange, true); Navigate(scrAppChange, ScreenTransition.Fade)
)""",
        children=[
            rect("recCard_Home", 8, 8, "Parent.TemplateWidth - 16", "Parent.TemplateHeight - 16",
                 border="If(ThisItem.IsSelected, gTheme.Primary, gTheme.Border)", OnSelect="Select(Parent)"),
            rect("recCardAccent_Home", 8, 8, 4, "Parent.TemplateHeight - 16", fill="gTheme.Primary", thickness=0, OnSelect="Select(Parent)"),
            icon("icoCard_Home",
                 'Switch(ThisItem.Key, "newApp", Icon.AddDocument, "exposeApi", Icon.Settings, "addAppRoles", Icon.Lock, '
                 '"assignGroups", Icon.People, "createSP", Icon.Waffle, "group", Icon.AddUser, "onboardGroup", Icon.Search, Icon.DetailList)',
                 28, 28, 44, 44, color="gTheme.Primary", on_select="Select(Parent)", Fill="gTheme.PrimaryLight",
                 PaddingTop=10, PaddingBottom=10, PaddingLeft=10, PaddingRight=10),
            label("lblCardTitle_Home", "ThisItem.Title", 84, 26, "Parent.TemplateWidth - 140", 26, size=13, bold=True, OnSelect="Select(Parent)"),
            label("lblCardBadge_Home", "ThisItem.Badge", 84, 52, 90, 20, size=8, bold=True, color="gTheme.Primary",
                  Fill="gTheme.PrimaryLight", Align="Align.Center", Visible='ThisItem.Badge <> ""', OnSelect="Select(Parent)"),
            icon("icoCardGo_Home", "Icon.ChevronRight", "Parent.TemplateWidth - 52", 34, 24, 24, color="gTheme.Muted", on_select="Select(Parent)"),
            label("lblCardSub_Home", "ThisItem.Subtitle", 28, 82, "Parent.TemplateWidth - 64", 56, size=10, color="gTheme.Muted",
                  VerticalAlign="VerticalAlign.Top", Wrap="true", OnSelect="Select(Parent)"),
        ],
    )
    recent = gallery(
        "galRecent_Home", "FirstN(Sort(EntraRequests, ID, SortOrder.Descending), 7)", "Parent.Width - 368", 196, 336, "Parent.Height - 300", 66,
        on_select="Set(varSelectedReqId, ThisItem.ID); Navigate(scrMyRequests, ScreenTransition.Fade)",
        children=[
            label("lblRName_Home", "ThisItem.TargetDisplayName", 12, 8, "Parent.TemplateWidth - 150", 22, bold=True, OnSelect="Select(Parent)"),
            label("lblRMeta_Home", 'ThisItem.Title & "  ·  " & ThisItem.RequestType.Value', 12, 32, "Parent.TemplateWidth - 24", 20, size=9,
                  color="gTheme.Muted", OnSelect="Select(Parent)"),
            status_badge("lblRStatus_Home", "ThisItem.Status.Value", "Parent.TemplateWidth - 136", 8, 124, 22),
            rect("recRSep_Home", 12, "Parent.TemplateHeight - 1", "Parent.TemplateWidth - 24", 1, fill="gTheme.Border", thickness=0),
        ],
    )
    children = frame(s, q("What do you want to do?"),
                     q("Every request is approved by your manager and by the Entra ID team, then applied automatically — stamped with your appCatID."),
                     q("Home")) + [
        cards,
        rect("recRecent_Home", "Parent.Width - 384", 154, 360, "Parent.Height - 178"),
        label("lblRecentTitle_Home", q("Your recent requests"), "Parent.Width - 364", 164, 320, 28, size=12, bold=True),
        recent,
        label("lblRecentEmpty_Home", q("Nothing yet. Pick an operation on the left to raise your first request."),
              "Parent.Width - 364", 200, 320, 60, size=10, color="gTheme.Muted", Wrap="true", Visible="CountRows(galRecent_Home.AllItems) = 0"),
        button("btnAllRequests_Home", q("View all my requests"), "Set(varSelectedReqId, Blank()); Navigate(scrMyRequests, ScreenTransition.Fade)",
               "Parent.Width - 364", "Parent.Height - 76", 320, 36, kind="secondary"),
    ]
    write("scrHome", root(s, children), "Home: operation cards + recent requests")


# ============================================================================ scrNewApp
def steps_nav(s: str) -> list:
    return [
        rect(f"recSteps_{s}", 24, 146, 256, "Parent.Height - 146 - 80"),
        gallery(f"galSteps_{s}", "gSteps", 24, 156, 256, 340, 64,
                on_select="If(ThisItem.Step <= varMaxStep, Set(varStep, ThisItem.Step))",
                children=[
                    rect(f"recStepSel_{s}", 0, 8, 4, 48, fill="If(ThisItem.Step = varStep, gTheme.Primary, RGBA(0, 0, 0, 0))", thickness=0,
                         OnSelect="Select(Parent)"),
                    label(f"lblStepNum_{s}", 'If(ThisItem.Step < varStep, "✓", Text(ThisItem.Step))', 18, 16, 32, 32, size=11, bold=True,
                          color="If(ThisItem.Step = varStep, RGBA(255, 255, 255, 1), If(ThisItem.Step <= varMaxStep, gTheme.Primary, gTheme.Muted))",
                          Fill="If(ThisItem.Step = varStep, gTheme.Primary, If(ThisItem.Step <= varMaxStep, gTheme.PrimaryLight, gTheme.Bg))",
                          Align="Align.Center", OnSelect="Select(Parent)"),
                    label(f"lblStepTitle_{s}", "ThisItem.Title", 60, 10, 186, 24, size=11, bold=True,
                          color="If(ThisItem.Step = varStep, gTheme.Text, If(ThisItem.Step <= varMaxStep, gTheme.Text, gTheme.Muted))",
                          OnSelect="Select(Parent)"),
                    label(f"lblStepHint_{s}", "ThisItem.Hint", 60, 34, 190, 20, size=9, color="gTheme.Muted", OnSelect="Select(Parent)"),
                ]),
        label(f"lblStepNote_{s}", q("Only Basics is required. Use Next for optional configuration, or Submit at any step."),
              40, 512, 224, 64, size=9, color="gTheme.Muted", Wrap="true", VerticalAlign="VerticalAlign.Top"),
    ]


def step_container(s: str, n: int, children: list) -> dict:
    return container(f"cntStep{n}_{s}", 320, 162, "Parent.Width - 360", "Parent.Height - 162 - 92", children, Visible=f"varStep = {n}")


def section_head(name: str, title: str, sub: str) -> list:
    return [
        label(f"lbl{name}Head", q(title), 0, 0, "Parent.Width", 28, size=14, bold=True),
        label(f"lbl{name}Sub", q(sub), 0, 28, "Parent.Width", 22, size=10, color="gTheme.Muted"),
    ]


def scopes_editor(s: str, top: int, enabled: str, gallery_h: str = "120") -> list:
    """Editable list of delegated scopes over colScopes (shared by the wizard and the change screen)."""
    add_access = ('If(CountRows(Filter(colScopes, Value = "access_as_user")) = 0, Collect(colScopes, {Key: Text(GUID()), Value: "access_as_user", '
                  'Type: "User", AdminName: "Access " & {app}, AdminDesc: "Allows the app to call " & {app} & " on behalf of the signed-in user."}))')
    app_name = "Trim(txtAppName_NewApp.Text)" if s == "NewApp" else "varApp.Title"
    return [
        label(f"lblScopes_{s}", q("Scopes (delegated permissions)"), 0, top, 400, 24, size=11, bold=True),
        button(f"btnAddAccess_{s}", q("＋ access_as_user"), add_access.replace("{app}", app_name), "Parent.Width - 330", top - 4, 170, 32,
               kind="secondary", DisplayMode=f"If({enabled}, DisplayMode.Edit, DisplayMode.Disabled)"),
        button(f"btnAddScope_{s}", q("＋ Custom scope"),
               'Collect(colScopes, {Key: Text(GUID()), Value: "", Type: "User", AdminName: "", AdminDesc: ""})',
               "Parent.Width - 150", top - 4, 150, 32, kind="subtle", DisplayMode=f"If({enabled}, DisplayMode.Edit, DisplayMode.Disabled)"),
        hint(f"lblScopeColName_{s}", q("Scope name"), 0, top + 32, 180),
        hint(f"lblScopeColType_{s}", q("Who can consent"), 190, top + 32, 120),
        hint(f"lblScopeColAdmin_{s}", q("Admin consent display name"), 320, top + 32, "(Parent.Width - 370) / 2"),
        hint(f"lblScopeColDesc_{s}", q("Admin consent description"), "330 + (Parent.Width - 370) / 2", top + 32, "(Parent.Width - 370) / 2"),
        gallery(f"galScopes_{s}", "colScopes", 0, top + 54, "Parent.Width", gallery_h, 46,
                DisplayMode=f"If({enabled}, DisplayMode.Edit, DisplayMode.Disabled)",
                children=[
                    text_input(f"txtScopeValue_{s}", "ThisItem.Value", q("access_as_user"), 0, 4, 180, 36,
                               OnChange="Patch(colScopes, ThisItem, {Value: Trim(Self.Text)})"),
                    dropdown(f"ddScopeType_{s}", '["User", "Admin"]', "ThisItem.Type", 190, 4, 120, 36,
                             OnChange="Patch(colScopes, ThisItem, {Type: Self.Selected.Value})"),
                    text_input(f"txtScopeName_{s}", "ThisItem.AdminName", q("Admin consent display name"), 320, 4,
                               "(Parent.TemplateWidth - 370) / 2", 36, OnChange="Patch(colScopes, ThisItem, {AdminName: Self.Text})"),
                    text_input(f"txtScopeDesc_{s}", "ThisItem.AdminDesc", q("Admin consent description"),
                               "330 + (Parent.TemplateWidth - 370) / 2", 4, "(Parent.TemplateWidth - 370) / 2", 36,
                               OnChange="Patch(colScopes, ThisItem, {AdminDesc: Self.Text})"),
                    icon(f"icoScopeRemove_{s}", "Icon.Trash", "Parent.TemplateWidth - 32", 10, 24, 24, color="gTheme.Danger",
                         on_select="Remove(colScopes, ThisItem)"),
                ]),
        hint(f"lblNoScopes_{s}", q("No scopes yet. Most APIs publish access_as_user."), 0, top + 62, "Parent.Width",
             Visible="CountRows(colScopes) = 0"),
    ]


def roles_editor(s: str, top: int, inline_mode: str) -> list:
    """Editable app roles over colRoles; the groups each role gets live in colRoleGroups."""
    return [
        hint(f"lblRoleColValue_{s}", q("Value (in the roles claim)"), 12, top, 200),
        hint(f"lblRoleColName_{s}", q("Display name"), 222, top, 230),
        hint(f"lblRoleColMembers_{s}", q("Allowed members"), 462, top, 160),
        gallery(f"galRoles_{s}", "colRoles", 0, top + 22, "Parent.Width", f"Parent.Height - {top + 22}", 136, children=[
            rect(f"recRole_{s}", 0, 4, "Parent.TemplateWidth", 126, fill="RGBA(250, 249, 248, 1)"),
            text_input(f"txtRoleValue_{s}", "ThisItem.Value", q("Orders.Admin"), 12, 14, 200, 36,
                       OnChange="Patch(colRoles, ThisItem, {Value: Trim(Self.Text)})"),
            text_input(f"txtRoleName_{s}", "ThisItem.DisplayName", q("Display name"), 222, 14, 230, 36,
                       OnChange="Patch(colRoles, ThisItem, {DisplayName: Self.Text})"),
            dropdown(f"ddRoleMembers_{s}", '["Users/Groups", "Applications", "Both"]', "ThisItem.Members", 462, 14, 160, 36,
                     OnChange="Patch(colRoles, ThisItem, {Members: Self.Selected.Value})"),
            icon(f"icoRoleRemove_{s}", "Icon.Trash", "Parent.TemplateWidth - 36", 20, 24, 24, color="gTheme.Danger",
                 on_select="RemoveIf(colRoleGroups, RoleKey = ThisItem.Key); Remove(colRoles, ThisItem)"),
            text_input(f"txtRoleDesc_{s}", "ThisItem.Description", q("Description (shown when assigning the role)"), 12, 54, 610, 36,
                       OnChange="Patch(colRoles, ThisItem, {Description: Self.Text})"),
            label(f"lblRoleGroupsCap_{s}", q("Groups:"), 12, 98, 60, 24, size=10, bold=True),
            label(f"lblRoleGroups_{s}",
                  'Coalesce(Concat(Filter(colRoleGroups, RoleKey = ThisItem.Key), DisplayName & If(Mode = "new", " (new)", ""), ",  "), '
                  '"None — nobody holds this role yet")', 72, 98, "Parent.TemplateWidth - 560", 24, size=10,
                  color='If(CountRows(Filter(colRoleGroups, RoleKey = ThisItem.Key)) = 0, gTheme.Muted, gTheme.Text)'),
            combobox(f"cmbRoleGroup_{s}", "gMyGroups", '["Title"]', '["Title"]', "Parent.TemplateWidth - 480", 94, 210, 32,
                     placeholder="Add existing group",
                     OnChange='If(!IsBlank(Self.Selected.GroupId) && CountRows(Filter(colRoleGroups, RoleKey = ThisItem.Key && GroupId = Self.Selected.GroupId)) = 0, '
                              'Collect(colRoleGroups, {RoleKey: ThisItem.Key, Mode: "existing", GroupId: Self.Selected.GroupId, DisplayName: Self.Selected.Title, '
                              'Description: "", OwnerIds: ""})); Reset(Self)'),
            link(f"lnkRoleNewGroup_{s}", q("＋ Create new group"),
                 f'Set(varGroupMode, "{inline_mode}"); Set(varGroupForRole, ThisItem.Key); '
                 'Set(varGroupSuggest, "grp-" & Lower(Substitute(ThisItem.Value, ".", "-"))); Navigate(scrNewGroup, ScreenTransition.Fade)',
                 "Parent.TemplateWidth - 260", 98, 180, 24),
            icon(f"icoRoleClear_{s}", "Icon.Cancel", "Parent.TemplateWidth - 36", 98, 24, 24, color="gTheme.Muted",
                 on_select="RemoveIf(colRoleGroups, RoleKey = ThisItem.Key)",
                 Visible="CountRows(Filter(colRoleGroups, RoleKey = ThisItem.Key)) > 0", Tooltip=q("Remove all groups from this role")),
        ]),
    ]


def new_app() -> None:
    s = "NewApp"
    team = (f'If(varNewTeam.Mode = "new", varNewTeam, {{Mode: "existing", GroupId: cmbTeam_{s}.Selected.GroupId, '
            f'DisplayName: cmbTeam_{s}.Selected.Title, Description: "", OwnerIds: ""}})')

    step1 = step_container(s, 1, section_head(f"S1_{s}", "Basics", "The minimum needed to register the application. Everything after this step is optional.") + [
        field_label(f"lblName_{s}", "Display name", COL1_X, 64, COL_W, required=True),
        text_input(f"txtAppName_{s}", '""', q("orders-api"), COL1_X, 86, COL_W),
        hint(f"hntName_{s}", q("Shown in the Entra admin center and on consent screens."), COL1_X, 124, COL_W),
        field_label(f"lblAppCat_{s}", "appCatID", COL2_X, 64, COL_W, required=True),
        text_input(f"txtAppCatId_{s}", 'Coalesce(First(Filter(gMyGroups, !IsBlank(AppCatId))).AppCatId, "")', q("APPCAT-001"), COL2_X, 86, COL_W),
        hint(f"hntAppCat_{s}", q("Your application catalogue id. Stamped on every object this request creates."), COL2_X, 124, COL_W),

        field_label(f"lblAudience_{s}", "Supported account types", COL1_X, 154, COL_W),
        radio(f"radAudience_{s}", '["Single tenant", "Multitenant"]', q("Single tenant"), COL1_X, 176, COL_W, 36),
        hint(f"hntAudience_{s}", q("Single tenant: only accounts in this organization (recommended)."), COL1_X, 212, COL_W),
        field_label(f"lblTeam_{s}", "Owning team", COL2_X, 154, COL_W, required=True),
        combobox(f"cmbTeam_{s}", "gMyTeams", '["Title"]', '["Title"]', COL2_X, 176, COL_W, placeholder="Choose a group you are a member of",
                 Visible='varNewTeam.Mode <> "new"', OnChange=f"Set(varNewTeam, {NO_TEAM})"),
        label(f"lblNewTeam_{s}", '"New team group: " & varNewTeam.DisplayName & "  (created when approved)"', COL2_X, 176,
              f"{COL_W} - 40", 36, size=10, bold=True, color="gTheme.Primary", Fill="gTheme.PrimaryLight", PaddingLeft="10",
              Visible='varNewTeam.Mode = "new"'),
        icon(f"icoClearTeam_{s}", "Icon.Cancel", f"{COL2_X} + {COL_W} - 32", 182, 24, 24, color="gTheme.Muted",
             on_select=f"Set(varNewTeam, {NO_TEAM})", Visible='varNewTeam.Mode = "new"'),
        link(f"lnkNewTeam_{s}", q("＋ Create new team group"),
             f'Set(varGroupMode, "inline-team"); Set(varGroupSuggest, "team-" & Lower(Substitute(Trim(txtAppName_{s}.Text), " ", "-"))); '
             "Navigate(scrNewGroup, ScreenTransition.Fade)", COL2_X, 214, 260),
        link(f"lnkAddExisting_{s}", q("Group not listed? Add an existing group"), "Navigate(scrAddGroup, ScreenTransition.Fade)",
             f"{COL2_X} + 262", 214, f"{COL_W} - 262"),

        field_label(f"lblJust_{s}", "Business justification", COL1_X, 248, COL_W, required=True),
        text_input(f"txtJustification_{s}", '""', q("Why is this needed, and for which service? Your manager and the Entra ID team read this."),
                   COL1_X, 270, COL_W, 76, multiline=True),
        field_label(f"lblDesc_{s}", "Description", COL2_X, 248, COL_W),
        text_input(f"txtDescription_{s}", '""', q("Optional"), COL2_X, 270, COL_W, 76, multiline=True),

        field_label(f"lblPlatform_{s}", "Redirect URI platform", COL1_X, 362, COL_W),
        dropdown(f"ddPlatform_{s}", '["None", "Web", "Single-page app"]', q("None"), COL1_X, 384, COL_W),
        field_label(f"lblRedirect_{s}", "Redirect URI(s)", COL2_X, 362, COL_W),
        text_input(f"txtRedirect_{s}", '""', q("https://app.contoso.com/signin-oidc   (separate several with ;)"), COL2_X, 384, COL_W,
                   DisplayMode=f'If(ddPlatform_{s}.Selected.Value = "None", DisplayMode.Disabled, DisplayMode.Edit)'),

        field_label(f"lblTicket_{s}", "Change ticket", COL1_X, 436, COL_W),
        text_input(f"txtTicket_{s}", '""', q("Optional, e.g. CHG0012345"), COL1_X, 458, COL_W),
    ])

    step2 = step_container(s, 2, section_head(f"S2_{s}", "Expose an API & token claims",
                                              "Let other applications request tokens for this app, and choose extra claims in the tokens it receives.") + [
        checkbox(f"chkExpose_{s}", q("Expose an API (set an Application ID URI so other apps can call this one)"), "false", 0, 60, "Parent.Width"),
        field_label(f"lblUri_{s}", "Application ID URI", 0, 100, 300),
        radio(f"radUri_{s}", '["api://{appId} (recommended)", "Custom"]', q("api://{appId} (recommended)"), 0, 122, 420, 36,
              DisplayMode=f"If(chkExpose_{s}.Value, DisplayMode.Edit, DisplayMode.Disabled)"),
        text_input(f"txtCustomUri_{s}", q("api://{appId}"), q("api://{tenantId}/orders  or  api://orders/{appId}"), 440, 122, 380,
                   Visible=f'chkExpose_{s}.Value && radUri_{s}.Selected.Value = "Custom"'),
        *scopes_editor(s, 176, f"chkExpose_{s}.Value"),
        label(f"lblClaims_{s}", q("Token claims"), 0, 362, 300, 24, size=11, bold=True),
        label(f"lblIdClaims_{s}", q("Optional claims in the ID token:"), 0, 392, 230, 30, size=10),
        checkbox(f"chkIdEmail_{s}", q("email"), "false", 230, 390, 100),
        checkbox(f"chkIdUpn_{s}", q("upn"), "false", 330, 390, 90),
        checkbox(f"chkIdGiven_{s}", q("given_name"), "false", 420, 390, 130),
        checkbox(f"chkIdFamily_{s}", q("family_name"), "false", 550, 390, 140),
        label(f"lblAtClaims_{s}", q("Optional claims in the access token:"), 0, 426, 230, 30, size=10),
        checkbox(f"chkAtEmail_{s}", q("email"), "false", 230, 424, 100),
        checkbox(f"chkAtUpn_{s}", q("upn"), "false", 330, 424, 90),
        checkbox(f"chkAtIdtyp_{s}", q("idtyp (app or user token)"), "false", 420, 424, 240),
        label(f"lblGroupsClaim_{s}", q("Groups claim:"), 0, 462, 230, 30, size=10),
        dropdown(f"ddGroupsClaim_{s}", '["None", "SecurityGroup", "ApplicationGroup", "All"]', q("None"), 230, 458, 220, 34),
        hint(f"hntGroupsClaim_{s}", q("ApplicationGroup = only groups assigned to this app. Prefer app roles over group claims."), 460, 464, "Parent.Width - 460"),
    ])

    step3 = step_container(s, 3, section_head(f"S3_{s}", "App roles & groups",
                                              "Roles appear in the token's roles claim. Give each role a group — the group's owners then manage access without another request.") + [
        button(f"btnStdRoles_{s}", q("＋ User + Admin roles with groups"),
               f"""With({{n: Trim(txtAppName_{s}.Text)}},
    With({{p: Concat(Split(Substitute(n, " ", "-"), "-"), Upper(Left(Value, 1)) & Mid(Value, 2)), sl: Lower(Substitute(n, " ", "-")), k1: Text(GUID()), k2: Text(GUID())}},
        If(CountRows(Filter(colRoles, Value = p & ".User")) = 0,
            Collect(colRoles, {{Key: k1, Value: p & ".User", DisplayName: n & " User", Description: "Standard users of " & n, Members: "Users/Groups"}});
            Collect(colRoleGroups, {{RoleKey: k1, Mode: "new", GroupId: "", DisplayName: "grp-" & sl & "-users", Description: "Members hold the " & p & ".User role", OwnerIds: ""}})
        );
        If(CountRows(Filter(colRoles, Value = p & ".Admin")) = 0,
            Collect(colRoles, {{Key: k2, Value: p & ".Admin", DisplayName: n & " Admin", Description: "Administrators of " & n, Members: "Users/Groups"}});
            Collect(colRoleGroups, {{RoleKey: k2, Mode: "new", GroupId: "", DisplayName: "grp-" & sl & "-admins", Description: "Members hold the " & p & ".Admin role", OwnerIds: ""}})
        )
    )
)""", 0, 60, 290, 34, kind="secondary"),
        button(f"btnAddRole_{s}", q("＋ Custom role"),
               'Collect(colRoles, {Key: Text(GUID()), Value: "", DisplayName: "", Description: "", Members: "Users/Groups"})', 300, 60, 150, 34, kind="subtle"),
        *roles_editor(s, 108, "inline-role"),
        label(f"lblNoRoles_{s}", q("No app roles yet. Most applications want a User and an Admin role — add both, each with its own new group, in one click."),
              12, 140, "Parent.Width - 24", 48, size=10, color="gTheme.Muted", Wrap="true", Visible="CountRows(colRoles) = 0"),
    ])

    step4 = step_container(s, 4, section_head(f"S4_{s}", "Enterprise application & ownership",
                                              "The enterprise application (service principal) is what users sign in to and what holds role assignments.") + [
        field_label(f"lblCreateSp_{s}", "Create the enterprise application", 0, 64, 400),
        toggle(f"tglCreateSp_{s}", "true", 0, 86, DisplayMode="If(CountRows(colRoleGroups) > 0, DisplayMode.Disabled, DisplayMode.Edit)"),
        hint(f"hntCreateSp_{s}", q("Required for role assignments — always created when any role has groups."), 0, 122, "Parent.Width"),
        field_label(f"lblAssign_{s}", "Assignment required", 0, 156, 400),
        toggle(f"tglAssign_{s}", "true", 0, 178),
        hint(f"hntAssign_{s}", q("Only users in an assigned group can sign in or get tokens. Recommended."), 0, 214, "Parent.Width"),
        field_label(f"lblOwners_{s}", "Additional owners", 0, 248, COL_W),
        combobox(f"cmbOwners_{s}", USERS, '["DisplayName", "Mail"]', '["DisplayName"]', 0, 270, COL_W, multi=True, placeholder="Search people"),
        hint(f"hntOwners_{s}", q("You are always an owner. Owners can manage the app registration in the Entra admin center."), 0, 308, COL_W),
        field_label(f"lblTags_{s}", "Optional tags", 0, 342, "Parent.Width"),
        text_input(f"txtTags_{s}", '""', q("costCentre=CC-4410; project=atlas"), 0, 364, "Parent.Width"),
        hint(f"hntTags_{s}", q("appCatID, team, createdBy, requestId and the other platform tags are added automatically."), 0, 402, "Parent.Width"),
    ])

    review_html = f"""With({{team: {team}}},
"<div style='font-family:Segoe UI, sans-serif; font-size:13px; color:#323130; line-height:1.5'>" &
"<table style='border-collapse:collapse; width:100%'>" &
"<tr><td style='color:#605e5c; width:220px; padding:4px 0'>Display name</td><td><b>" & Trim(txtAppName_{s}.Text) & "</b></td></tr>" &
"<tr><td style='color:#605e5c; padding:4px 0'>appCatID</td><td>" & Upper(Trim(txtAppCatId_{s}.Text)) & "</td></tr>" &
"<tr><td style='color:#605e5c; padding:4px 0'>Account types</td><td>" & radAudience_{s}.Selected.Value & "</td></tr>" &
"<tr><td style='color:#605e5c; padding:4px 0'>Owning team</td><td>" & team.DisplayName & If(team.Mode = "new", " <i>(new group)</i>", "") & "</td></tr>" &
"<tr><td style='color:#605e5c; padding:4px 0'>Redirect URIs</td><td>" & If(ddPlatform_{s}.Selected.Value = "None", "none", ddPlatform_{s}.Selected.Value & ": " & txtRedirect_{s}.Text) & "</td></tr>" &
"<tr><td style='color:#605e5c; padding:4px 0'>Expose an API</td><td>" & If(chkExpose_{s}.Value, If(radUri_{s}.Selected.Value = "Custom", txtCustomUri_{s}.Text, "api://{{appId}}") & If(CountRows(colScopes) > 0, " — scopes: " & Concat(colScopes, Value, ", "), ""), "no") & "</td></tr>" &
"<tr><td style='color:#605e5c; padding:4px 0'>Groups claim</td><td>" & ddGroupsClaim_{s}.Selected.Value & "</td></tr>" &
"<tr><td style='color:#605e5c; padding:4px 0; vertical-align:top'>App roles</td><td>" &
    If(CountRows(colRoles) = 0, "none", "<ul style='margin:0; padding-left:18px'>" &
        Concat(ForAll(colRoles As r, {{t: "<li><b>" & r.Value & "</b> → " & Coalesce(Concat(Filter(colRoleGroups, RoleKey = r.Key), DisplayName & If(Mode = "new", " <i>(new)</i>", ""), ", "), "<i>no groups</i>") & "</li>"}}), t) & "</ul>") & "</td></tr>" &
"<tr><td style='color:#605e5c; padding:4px 0'>Enterprise app</td><td>" & If(tglCreateSp_{s}.Value || CountRows(colRoleGroups) > 0, "yes" & If(tglAssign_{s}.Value, ", assignment required", ""), "no") & "</td></tr>" &
"<tr><td style='color:#605e5c; padding:4px 0'>Additional owners</td><td>" & Coalesce(Concat(cmbOwners_{s}.SelectedItems, DisplayName, ", "), "none") & "</td></tr>" &
"</table>" &
"<p style='margin-top:14px; padding:10px 12px; background:#ebf3fc; border-left:3px solid #0f6cbd'><b>What happens next</b><br>" &
"1. Your manager approves in Outlook / Teams.  2. The Entra ID team approves.  3. The app registration, roles, groups and enterprise app are created automatically and appear under My requests.</p>" &
"</div>"
)"""
    step5 = step_container(s, 5, section_head(f"S5_{s}", "Review + submit", "Check the request. You can still go back to any section.") + [
        html(f"htmlReview_{s}", review_html, 0, 60, "Parent.Width", "Parent.Height - 60"),
    ])

    err1 = f"""Coalesce(
    If(Len(Trim(txtAppName_{s}.Text)) < 3, "Display name is required (3+ characters)."),
    If(!IsMatch(Trim(txtAppName_{s}.Text), "^[^""\\\\]{{1,120}}$"), "Display name cannot contain double quotes or backslashes (max 120 characters)."),
    If(!IsMatch(Upper(Trim(txtAppCatId_{s}.Text)), gAppCatPattern), "appCatID looks like APPCAT-001."),
    If(varNewTeam.Mode <> "new" && IsBlank(cmbTeam_{s}.Selected.GroupId), "Choose the owning team, or create a new team group."),
    If(Len(Trim(txtJustification_{s}.Text)) < 10, "Business justification is required (10+ characters)."),
    If(ddPlatform_{s}.Selected.Value <> "None" && !IsMatch(Trim(txtRedirect_{s}.Text), "^\\S+$"), "Redirect URIs: no spaces; separate several with ;")
)"""
    err2 = f"""Coalesce(
    If(chkExpose_{s}.Value && radUri_{s}.Selected.Value = "Custom" && !IsMatch(Trim(txtCustomUri_{s}.Text), "^(api://|https://)\\S+$"), "The custom Application ID URI must start with api:// or https://"),
    If(CountRows(Filter(colScopes, !IsMatch(Value, gValuePattern) || IsBlank(Trim(AdminName)) || IsBlank(Trim(AdminDesc)))) > 0, "Each scope needs a name (letters, digits, . _ -), an admin consent display name and a description."),
    If(CountRows(colScopes) <> CountRows(Distinct(colScopes, Value)), "Scope names must be unique.")
)"""
    err3 = """Coalesce(
    If(CountRows(Filter(colRoles, !IsMatch(Value, gValuePattern) || IsBlank(Trim(DisplayName)) || IsBlank(Trim(Description)))) > 0, "Each role needs a value (letters, digits, . _ -), a display name and a description."),
    If(CountRows(colRoles) <> CountRows(Distinct(colRoles, Value)), "Role values must be unique.")
)"""

    payload = f"""With({{team: {team}}},
JSON({{
    displayName: Trim(txtAppName_{s}.Text),
    description: {clean(f"txtDescription_{s}.Text")},
    signInAudience: If(radAudience_{s}.Selected.Value = "Multitenant", "AzureADMultipleOrgs", "AzureADMyOrg"),
    owningGroup: {{mode: team.Mode, id: team.GroupId, displayName: team.DisplayName, description: team.Description, ownerIds: team.OwnerIds}},
    redirectUrisWeb: If(ddPlatform_{s}.Selected.Value = "Web", Trim(txtRedirect_{s}.Text), ""),
    redirectUrisSpa: If(ddPlatform_{s}.Selected.Value = "Single-page app", Trim(txtRedirect_{s}.Text), ""),
    exposeApi: {{
        enabled: chkExpose_{s}.Value,
        identifierUriTemplate: If(radUri_{s}.Selected.Value = "Custom", Trim(txtCustomUri_{s}.Text), "api://{{appId}}"),
        scopes: If(chkExpose_{s}.Value, ForAll(colScopes, {{value: ThisRecord.Value, type: ThisRecord.Type, adminConsentDisplayName: ThisRecord.AdminName, adminConsentDescription: ThisRecord.AdminDesc}}), Filter(ForAll(colScopes, {{value: ThisRecord.Value, type: ThisRecord.Type, adminConsentDisplayName: ThisRecord.AdminName, adminConsentDescription: ThisRecord.AdminDesc}}), false))
    }},
    optionalClaimsIdToken: Concat(Filter(Table({{n: "email", on: chkIdEmail_{s}.Value}}, {{n: "upn", on: chkIdUpn_{s}.Value}}, {{n: "given_name", on: chkIdGiven_{s}.Value}}, {{n: "family_name", on: chkIdFamily_{s}.Value}}), on), n, ","),
    optionalClaimsAccessToken: Concat(Filter(Table({{n: "email", on: chkAtEmail_{s}.Value}}, {{n: "upn", on: chkAtUpn_{s}.Value}}, {{n: "idtyp", on: chkAtIdtyp_{s}.Value}}), on), n, ","),
    groupMembershipClaims: ddGroupsClaim_{s}.Selected.Value,
    appRoles: ForAll(colRoles As r, {{
        value: r.Value, displayName: r.DisplayName, description: r.Description,
        allowedMemberTypes: Switch(r.Members, "Applications", "Application", "Both", "User,Application", "User"),
        assignGroups: ForAll(Filter(colRoleGroups, RoleKey = r.Key) As g, {{mode: g.Mode, id: g.GroupId, displayName: g.DisplayName, description: g.Description, ownerIds: g.OwnerIds}})
    }}),
    createServicePrincipal: tglCreateSp_{s}.Value || CountRows(colRoleGroups) > 0,
    appRoleAssignmentRequired: tglAssign_{s}.Value,
    additionalOwnerIds: Concat(cmbOwners_{s}.SelectedItems, Id, ";"),
    tags: Trim(txtTags_{s}.Text)
}}, JSONFormat.Compact)
)"""
    submit = f"""With({{err: lblErrAll_{s}.Text}},
    If(!IsBlank(err),
        Notify(err, NotificationType.Warning),
        {NEW_REQ_ID};
        IfError(
            Patch(EntraRequests, Defaults(EntraRequests), {{
                Title: varReqId,
                RequestType: {{Value: "createAppRegistration"}},
                Status: {{Value: "Submitted"}},
                AppCatId: Upper(Trim(txtAppCatId_{s}.Text)),
                TargetDisplayName: Trim(txtAppName_{s}.Text),
                Justification: Trim(txtJustification_{s}.Text),
                TicketReference: Trim(txtTicket_{s}.Text),
                PayloadJson: {payload.replace(chr(10), chr(10) + "                ")}
            }}),
            Notify("The request could not be submitted: " & FirstError.Message, NotificationType.Error),
            Notify("Request " & varReqId & " submitted. Your manager has been asked to approve it.", NotificationType.Success);
            Set(varResetNewApp, true);
            Set(varSelectedReqId, Blank());
            Navigate(scrMyRequests, ScreenTransition.Fade)
        )
    )
)"""
    next_ = f"""With({{err: Switch(varStep, 1, lblErr1_{s}.Text, 2, lblErr2_{s}.Text, 3, lblErr3_{s}.Text, "")}},
    If(IsBlank(err),
        Set(varStep, Min(varStep + 1, 5)); Set(varMaxStep, Max(varMaxStep, varStep)),
        Notify(err, NotificationType.Warning)
    )
)"""
    bar_y = "Parent.Height - 50"
    command_bar = [
        rect(f"recCmd_{s}", 0, "Parent.Height - 64", "Parent.Width", 64, border="gTheme.Border"),
        button(f"btnSubmit_{s}", q("Submit request"), submit, 320, bar_y, 170, 36),
        button(f"btnNext_{s}", q("Next  ›"), next_, 500, bar_y, 120, 36, kind="secondary", Visible="varStep < 5"),
        button(f"btnBack_{s}", q("‹  Previous"), "Set(varStep, Max(1, varStep - 1))", 630, bar_y, 120, 36, kind="subtle", Visible="varStep > 1"),
        button(f"btnCancel_{s}", q("Cancel"), "Set(varResetNewApp, true); Navigate(scrHome, ScreenTransition.Fade)",
               "Parent.Width - 144", bar_y, 120, 36, kind="subtle"),
        label(f"lblStepOf_{s}", '"Step " & varStep & " of 5"', 24, bar_y, 200, 36, size=10, color="gTheme.Muted"),
        label(f"lblErr1_{s}", err1, 0, 0, 10, 10, Visible="false"),
        label(f"lblErr2_{s}", err2, 0, 0, 10, 10, Visible="false"),
        label(f"lblErr3_{s}", err3, 0, 0, 10, 10, Visible="false"),
        label(f"lblErrAll_{s}", f"Coalesce(lblErr1_{s}.Text, lblErr2_{s}.Text, lblErr3_{s}.Text)", 0, 0, 10, 10, Visible="false"),
    ]

    children = frame(s, q("Register an application"),
                     q("App registration, Application ID URI, scopes, app roles, groups and enterprise app — in one request."),
                     q("Home  ›  App registrations  ›  Register an application")) + steps_nav(s) + [
        rect(f"recMain_{s}", 296, 146, "Parent.Width - 320", "Parent.Height - 146 - 80"),
        step1, step2, step3, step4, step5,
    ] + command_bar
    write("scrNewApp", root(s, children), "Register an application: 5-section wizard (Basics required; Submit / Next / Cancel)")


# ============================================================================ scrNewGroup
def new_group() -> None:
    s = "Group"
    standalone = 'varGroupMode = "standalone"'
    payload = f"""JSON({{
    displayName: Trim(txtGroupName_{s}.Text),
    description: {clean(f"txtGroupDesc_{s}.Text")},
    ownerIds: Concat(cmbGroupOwners_{s}.SelectedItems, Id, ";"),
    memberIds: Concat(cmbGroupMembers_{s}.SelectedItems, Id, ";")
}}, JSONFormat.Compact)"""
    primary = f"""With({{err: Coalesce(
        If(!IsMatch(Trim(txtGroupName_{s}.Text), "^[A-Za-z0-9][A-Za-z0-9 ._-]{{2,119}}$"), "Group name: 3-120 letters, digits, spaces, . _ or -"),
        If({standalone} && !IsMatch(Upper(Trim(txtGroupAppCat_{s}.Text)), gAppCatPattern), "appCatID looks like APPCAT-001."),
        If({standalone} && Len(Trim(txtGroupJust_{s}.Text)) < 10, "Business justification is required (10+ characters).")
    )}},
    If(!IsBlank(err),
        Notify(err, NotificationType.Warning),
        With({{g: {{Mode: "new", GroupId: "", DisplayName: Trim(txtGroupName_{s}.Text), Description: {clean(f"txtGroupDesc_{s}.Text")}, OwnerIds: Concat(cmbGroupOwners_{s}.SelectedItems, Id, ";")}}}},
            Switch(varGroupMode,
                "inline-team", Set(varNewTeam, g); Back(),
                "inline-role", Collect(colRoleGroups, {{RoleKey: varGroupForRole, Mode: "new", GroupId: "", DisplayName: g.DisplayName, Description: g.Description, OwnerIds: g.OwnerIds}}); Back(),
                "inline-assign", Collect(colAssign, {{RoleId: varAssignRole.Id, RoleValue: varAssignRole.Value, Mode: "new", GroupId: "", DisplayName: g.DisplayName, Description: g.Description, OwnerIds: g.OwnerIds}}); Back(),
                {NEW_REQ_ID};
                IfError(
                    Patch(EntraRequests, Defaults(EntraRequests), {{
                        Title: varReqId,
                        RequestType: {{Value: "createGroup"}},
                        Status: {{Value: "Submitted"}},
                        AppCatId: Upper(Trim(txtGroupAppCat_{s}.Text)),
                        TargetDisplayName: Trim(txtGroupName_{s}.Text),
                        Justification: Trim(txtGroupJust_{s}.Text),
                        PayloadJson: {payload.replace(chr(10), chr(10) + "                        ")}
                    }}),
                    Notify("The request could not be submitted: " & FirstError.Message, NotificationType.Error),
                    Notify("Request " & varReqId & " submitted for approval.", NotificationType.Success); Set(varSelectedReqId, Blank()); Navigate(scrMyRequests, ScreenTransition.Fade)
                )
            )
        )
    )
)"""
    form = container(f"cntGroup_{s}", 48, 170, "Parent.Width - 96", "Parent.Height - 170 - 92", [
        field_label(f"lblGName_{s}", "Group name", COL1_X, 0, COL_W, required=True),
        text_input(f"txtGroupName_{s}", "varGroupSuggest", q("grp-orders-admins"), COL1_X, 22, COL_W),
        hint(f"hntGName_{s}", q("Security group. A unique mail nickname is generated automatically."), COL1_X, 60, COL_W),
        field_label(f"lblGAppCat_{s}", "appCatID", COL2_X, 0, COL_W, required=True, ),
        # Inline groups inherit the appCatID of the request they belong to: shown read-only.
        text_input(f"txtGroupAppCat_{s}",
                   f'If({standalone}, Coalesce(First(Filter(gMyGroups, !IsBlank(AppCatId))).AppCatId, ""), '
                   f'varGroupMode = "inline-assign", varApp.AppCatId, txtAppCatId_NewApp.Text)',
                   q("APPCAT-001"), COL2_X, 22, COL_W,
                   DisplayMode=f"If({standalone}, DisplayMode.Edit, DisplayMode.View)"),
        hint(f"hntGAppCat_{s}", q("Taken from the request this group belongs to; it can't differ."), COL2_X, 60, COL_W,
             Visible=f"!({standalone})"),
        field_label(f"lblGDesc_{s}", "Description", COL1_X, 96, "Parent.Width"),
        text_input(f"txtGroupDesc_{s}", '""', q("What membership of this group grants"), COL1_X, 118, "Parent.Width", 64, multiline=True),
        field_label(f"lblGOwners_{s}", "Additional owners", COL1_X, 196, COL_W),
        combobox(f"cmbGroupOwners_{s}", USERS, '["DisplayName", "Mail"]', '["DisplayName"]', COL1_X, 218, COL_W, multi=True,
                 placeholder="Optional: type a name to search"),
        field_label(f"lblGMembers_{s}", "Initial members", COL2_X, 196, COL_W),
        combobox(f"cmbGroupMembers_{s}", USERS, '["DisplayName", "Mail"]', '["DisplayName"]', COL2_X, 218, COL_W, multi=True,
                 placeholder=f'If({standalone}, "Optional: type a name to search", "Added by the owners after creation")',
                 DisplayMode=f"If({standalone}, DisplayMode.Edit, DisplayMode.Disabled)"),
        hint(f"hntGMembers_{s}", q("Groups created with a request start with owners only. Owners add members once it exists."),
             COL2_X, 256, COL_W, 36, Visible=f"!({standalone})"),
        field_label(f"lblGJust_{s}", "Business justification", COL1_X, 270, COL_W, required=True),
        text_input(f"txtGroupJust_{s}", '""', q("Why is this group needed?"), COL1_X, 292, COL_W, 64, multiline=True, Visible=standalone),
        hint(f"hntGJust_{s}", q("Inline groups are justified by the request they belong to."), COL1_X, 292, COL_W, 36, Visible=f"!({standalone})"),
        rect(f"recGInfo_{s}", COL1_X, 376, "Parent.Width", 64, fill="gTheme.PrimaryLight", border="gTheme.PrimaryLight"),
        label(f"lblGInfo_{s}",
              q("You will be an owner of this group. Owners add and remove members themselves in My Groups or the Entra admin center — "
                "that is how access to app roles is managed day to day, without new requests."),
              16, 382, "Parent.Width - 32", 52, size=10, Wrap="true", VerticalAlign="VerticalAlign.Middle"),
    ])
    children = frame(s, f'If({standalone}, "New security group", "New group for this request")',
                     f'If({standalone}, "Raise a request for a security group you own.", "The group is created when the request is approved, and is owned by you.")',
                     f'If({standalone}, "Home  ›  Groups  ›  New security group", "Home  ›  Register an application  ›  New group")') + [
        rect(f"recCard_{s}", 24, 146, "Parent.Width - 48", "Parent.Height - 146 - 80"),
        form,
        rect(f"recCmd_{s}", 0, "Parent.Height - 64", "Parent.Width", 64),
        button(f"btnGroupPrimary_{s}", f'If({standalone}, "Submit request", "Add to request")', primary, 24, "Parent.Height - 50", 170, 36),
        button(f"btnGroupCancel_{s}", q("Cancel"), "Back()", 204, "Parent.Height - 50", 120, 36, kind="subtle"),
    ]
    write("scrNewGroup", root(s, children), "New security group: standalone request, or inline group for the wizard / change screen")


# ============================================================================ scrAddGroup
def add_group() -> None:
    s = "AddGroup"
    gid = f"Lower(Trim(txtGroupId_{s}.Text))"
    submit = f"""If(
    !IsMatch({gid}, "^[0-9a-f]{{8}}-([0-9a-f]{{4}}-){{3}}[0-9a-f]{{12}}$"),
        Notify("Enter the group's Object ID: 32 hex digits in the form 00000000-0000-0000-0000-000000000000.", NotificationType.Warning),
    !IsBlank(LookUp(gMyGroups, GroupId = {gid})),
        Notify("This group is already available to you in the pickers.", NotificationType.Information),
    {NEW_REQ_ID};
    IfError(
        Patch(EntraRequests, Defaults(EntraRequests), {{
            Title: varReqId,
            RequestType: {{Value: "onboardGroup"}},
            Status: {{Value: "Submitted"}},
            TargetObjectId: {gid},
            TargetDisplayName: {gid},
            Justification: "Add an existing group to the self-service catalog",
            PayloadJson: JSON({{groupId: {gid}}}, JSONFormat.Compact)
        }}),
        Notify("The request could not be submitted: " & FirstError.Message, NotificationType.Error),
        Notify("Request " & varReqId & " submitted. The group appears in about a minute if you are a member or owner.", NotificationType.Success);
        Reset(txtGroupId_{s}); Refresh(EntraRequests)
    )
)"""
    history = gallery(
        f"galOnboard_{s}", 'FirstN(Sort(Filter(EntraRequests, RequestType.Value = "onboardGroup"), ID, SortOrder.Descending), 6)',
        0, 300, "Parent.Width", "Parent.Height - 300", 64,
        children=[
            label(f"lblOName_{s}", "ThisItem.TargetDisplayName", 12, 6, "Parent.TemplateWidth - 190", 22, bold=True),
            label(f"lblOMeta_{s}", 'ThisItem.Title & "  ·  " & Text(ThisItem.Created, "dd mmm yyyy hh:mm")', 12, 28, "Parent.TemplateWidth - 190", 18,
                  size=9, color="gTheme.Muted"),
            label(f"lblOError_{s}", "ThisItem.ErrorMessage", 12, 44, "Parent.TemplateWidth - 24", 18, size=9, color="gTheme.Danger",
                  Visible="!IsBlank(ThisItem.ErrorMessage)"),
            status_badge(f"lblOStatus_{s}", "ThisItem.Status.Value", "Parent.TemplateWidth - 166", 8, 150, 22),
            rect(f"recOSep_{s}", 12, "Parent.TemplateHeight - 1", "Parent.TemplateWidth - 24", 1, fill="gTheme.Border", thickness=0),
        ],
    )
    form = container(f"cntAddGroup_{s}", 48, 170, "Parent.Width - 96", "Parent.Height - 170 - 92", [
        field_label(f"lblGroupId_{s}", "Group Object ID", COL1_X, 0, COL_W, required=True),
        text_input(f"txtGroupId_{s}", '""', q("00000000-0000-0000-0000-000000000000"), COL1_X, 22, COL_W),
        hint(f"hntGroupId_{s}", q("Entra admin center → Groups → the group → Overview → Object ID."), COL1_X, 60, COL_W),
        rect(f"recInfo_{s}", COL2_X, 0, COL_W, 132, fill="gTheme.PrimaryLight", border="gTheme.PrimaryLight"),
        label(f"lblInfo_{s}",
              q("No approval is needed: nothing changes in Entra. A flow checks that you are a member or owner of the group and that it is a "
                "security group, then makes it selectable here. It appears for all its members and owners, usually within a minute, "
                "and is kept up to date every hour."),
              f"{COL2_X} + 14", 8, f"{COL_W} - 28", 116, size=10, Wrap="true", VerticalAlign="VerticalAlign.Top"),
        label(f"lblHistory_{s}", q("Your recent additions"), COL1_X, 264, COL_W, 28, size=12, bold=True),
        link(f"lnkRefresh_{s}", q("↻ Refresh"), "Refresh(EntraRequests); Refresh(EntraCatalogGroups)", f"Parent.Width - 120", 266, 120),
        history,
        label(f"lblHistoryEmpty_{s}", q("Nothing added yet."), COL1_X, 304, COL_W, 24, size=10, color="gTheme.Muted",
              Visible=f"CountRows(galOnboard_{s}.AllItems) = 0"),
    ])
    children = frame(s, q("Add an existing group"),
                     q("If a group you belong to isn't offered in the Owning team or group pickers, add it here."),
                     q("Home  ›  Groups  ›  Add existing group")) + [
        rect(f"recCard_{s}", 24, 146, "Parent.Width - 48", "Parent.Height - 146 - 80"),
        form,
        rect(f"recCmd_{s}", 0, "Parent.Height - 64", "Parent.Width", 64),
        button(f"btnSubmit_{s}", q("Add group"), submit, 24, "Parent.Height - 50", 170, 36),
        button(f"btnBack_{s}", q("Back"), "Back()", 204, "Parent.Height - 50", 120, 36, kind="subtle"),
    ]
    write("scrAddGroup", root(s, children), "Add an existing group to the catalog (request type onboardGroup, processed by flow ER-04)")


# ============================================================================ scrAppChange
def app_change() -> None:
    s = "Change"
    title = 'Switch(varOp, "exposeApi", "Expose an API", "addAppRoles", "App roles", "assignGroups", "Role assignments", "Enterprise application")'
    sub = ('Switch(varOp, "exposeApi", "Set the Application ID URI and publish scopes on an app your team owns.", '
           '"addAppRoles", "Add app roles, optionally with a group for each role.", '
           '"assignGroups", "Give Entra groups an app role. Group owners then manage who has access.", '
           '"Create the service principal for an existing app registration.")')
    scope_rec = "{value: ThisRecord.Value, type: ThisRecord.Type, adminConsentDisplayName: ThisRecord.AdminName, adminConsentDescription: ThisRecord.AdminDesc}"
    roles_json = ('ForAll(colRoles As r, {value: r.Value, displayName: r.DisplayName, description: r.Description, '
                  'allowedMemberTypes: Switch(r.Members, "Applications", "Application", "Both", "User,Application", "User"), '
                  'assignGroups: ForAll(Filter(colRoleGroups, RoleKey = r.Key) As g, {mode: g.Mode, id: g.GroupId, displayName: g.DisplayName, description: g.Description, ownerIds: g.OwnerIds})})')
    submit = f"""With({{err: Coalesce(
        If(IsBlank(varApp), "Choose an application on the left."),
        If(Len(Trim(txtJust_{s}.Text)) < 10, "Business justification is required (10+ characters)."),
        If(varOp = "exposeApi" && radUri_{s}.Selected.Value = "Custom" && !IsMatch(Trim(txtCustomUri_{s}.Text), "^(api://|https://)\\S+$"), "The custom Application ID URI must start with api:// or https://"),
        If(varOp = "exposeApi" && CountRows(Filter(colScopes, !IsMatch(Value, gValuePattern) || IsBlank(Trim(AdminName)) || IsBlank(Trim(AdminDesc)))) > 0, "Each scope needs a name, an admin consent display name and a description."),
        If(varOp = "addAppRoles" && (CountRows(colRoles) = 0 || CountRows(Filter(colRoles, !IsMatch(Value, gValuePattern) || IsBlank(Trim(DisplayName)) || IsBlank(Trim(Description)))) > 0), "Add at least one role with a value, display name and description."),
        If(varOp = "assignGroups" && CountRows(colAssign) = 0, "Add at least one role assignment."),
        If(varOp = "createSP" && !IsBlank(varApp.ServicePrincipalId), "This app already has an enterprise application.")
    )}},
    If(!IsBlank(err),
        Notify(err, NotificationType.Warning),
        {NEW_REQ_ID};
        With({{
            type: Switch(varOp, "exposeApi", "exposeApi", "addAppRoles", "addAppRoles", "assignGroups", "assignGroupsToAppRoles", "createServicePrincipal"),
            payload: Switch(varOp,
                "exposeApi", JSON({{applicationObjectId: varApp.ObjectId, applicationDisplayName: varApp.Title, identifierUriTemplate: If(radUri_{s}.Selected.Value = "Custom", Trim(txtCustomUri_{s}.Text), "api://{{appId}}"), scopes: ForAll(colScopes, {scope_rec})}}, JSONFormat.Compact),
                "addAppRoles", JSON({{applicationObjectId: varApp.ObjectId, applicationDisplayName: varApp.Title, appRoles: {roles_json}}}, JSONFormat.Compact),
                "assignGroups", JSON({{applicationObjectId: varApp.ObjectId, applicationDisplayName: varApp.Title, assignments: ForAll(colAssign, {{appRoleId: ThisRecord.RoleId, appRoleValue: ThisRecord.RoleValue, mode: ThisRecord.Mode, id: ThisRecord.GroupId, displayName: ThisRecord.DisplayName, description: ThisRecord.Description, ownerIds: ThisRecord.OwnerIds}})}}, JSONFormat.Compact),
                JSON({{applicationObjectId: varApp.ObjectId, applicationDisplayName: varApp.Title, appRoleAssignmentRequired: tglAssign_{s}.Value}}, JSONFormat.Compact)
            )
        }},
            IfError(
                Patch(EntraRequests, Defaults(EntraRequests), {{
                    Title: varReqId,
                    RequestType: {{Value: type}},
                    Status: {{Value: "Submitted"}},
                    AppCatId: varApp.AppCatId,
                    TargetDisplayName: varApp.Title,
                    TargetObjectId: varApp.ObjectId,
                    Justification: Trim(txtJust_{s}.Text),
                    TicketReference: Trim(txtTicket_{s}.Text),
                    PayloadJson: payload
                }}),
                Notify("The request could not be submitted: " & FirstError.Message, NotificationType.Error),
                Notify("Request " & varReqId & " submitted for approval.", NotificationType.Success); Set(varResetChange, true); Set(varSelectedReqId, Blank()); Navigate(scrMyRequests, ScreenTransition.Fade)
            )
        )
    )
)"""
    role_items = 'ForAll(Table(ParseJSON(Coalesce(varApp.AppRolesJson, "[]"))), {Id: Text(ThisRecord.Value.id), Value: Text(ThisRecord.Value.value)})'
    sections_h = "Parent.Height - 96 - 150"
    expose = container(f"cntExpose_{s}", 0, 96, "Parent.Width", sections_h, [
        field_label(f"lblUri_{s}", "Application ID URI (added; existing URIs are kept)", 0, 0, 420),
        radio(f"radUri_{s}", '["api://{appId} (recommended)", "Custom"]', q("api://{appId} (recommended)"), 0, 22, 420, 36),
        text_input(f"txtCustomUri_{s}", q("api://{appId}"), q("api://{tenantId}/orders"), 440, 22, 360, Visible=f'radUri_{s}.Selected.Value = "Custom"'),
        hint(f"lblExistingScopes_{s}",
             '"Existing scopes: " & Coalesce(Concat(Table(ParseJSON(Coalesce(varApp.ScopesJson, "[]"))), Text(ThisRecord.Value.value), ", "), "none")',
             0, 66, "Parent.Width"),
        *scopes_editor(s, 100, "true", "Parent.Height - 154"),
    ], Visible='varOp = "exposeApi"')
    roles = container(f"cntRoles_{s}", 0, 96, "Parent.Width", sections_h, [
        hint(f"lblExistingRoles_{s}",
             '"Existing roles: " & Coalesce(Concat(Table(ParseJSON(Coalesce(varApp.AppRolesJson, "[]"))), Text(ThisRecord.Value.value), ", "), "none")',
             0, 0, "Parent.Width - 180"),
        button(f"btnAddRole_{s}", q("＋ Add role"),
               'Collect(colRoles, {Key: Text(GUID()), Value: "", DisplayName: "", Description: "", Members: "Users/Groups"})',
               "Parent.Width - 150", -4, 150, 32, kind="secondary"),
        *roles_editor(s, 36, "inline-role"),
    ], Visible='varOp = "addAppRoles"')
    assign = container(f"cntAssign_{s}", 0, 96, "Parent.Width", sections_h, [
        field_label(f"lblARole_{s}", "App role", 0, 0, 240),
        dropdown(f"ddRole_{s}", role_items, '""', 0, 22, 240),
        field_label(f"lblAGroup_{s}", "Group", 250, 0, 300),
        combobox(f"cmbGroup_{s}", "gMyGroups", '["Title"]', '["Title"]', 250, 22, 300, placeholder="Choose one of your groups"),
        button(f"btnAddAssign_{s}", q("Add"),
               f'If(!IsBlank(ddRole_{s}.Selected.Id) && !IsBlank(cmbGroup_{s}.Selected.GroupId), Collect(colAssign, {{RoleId: ddRole_{s}.Selected.Id, RoleValue: ddRole_{s}.Selected.Value, '
               f'Mode: "existing", GroupId: cmbGroup_{s}.Selected.GroupId, DisplayName: cmbGroup_{s}.Selected.Title, Description: "", OwnerIds: ""}}); Reset(cmbGroup_{s}))',
               560, 22, 90, 36),
        link(f"lnkNewGroup_{s}", q("＋ Create new group"),
             f'If(IsBlank(ddRole_{s}.Selected.Id), Notify("Choose the app role first.", NotificationType.Information), '
             f'Set(varGroupMode, "inline-assign"); Set(varAssignRole, ddRole_{s}.Selected); '
             f'Set(varGroupSuggest, "grp-" & Lower(Substitute(ddRole_{s}.Selected.Value, ".", "-"))); Navigate(scrNewGroup, ScreenTransition.Fade))',
             665, 28, 180),
        gallery(f"galAssign_{s}", "colAssign", 0, 72, "Parent.Width", "Parent.Height - 72", 44, children=[
            label(f"lblAssignRow_{s}", 'ThisItem.RoleValue & "   →   " & ThisItem.DisplayName & If(ThisItem.Mode = "new", "   (new group)", "")',
                  8, 8, "Parent.TemplateWidth - 56", 28, size=11),
            icon(f"icoAssignRemove_{s}", "Icon.Trash", "Parent.TemplateWidth - 36", 10, 24, 24, color="gTheme.Danger", on_select="Remove(colAssign, ThisItem)"),
            rect(f"recAssignSep_{s}", 8, 43, "Parent.TemplateWidth - 16", 1, fill="gTheme.Border", thickness=0),
        ]),
        hint(f"lblNoAssign_{s}", q("No assignments yet. Pick a role and a group, then Add."), 0, 80, "Parent.Width", Visible="CountRows(colAssign) = 0"),
    ], Visible='varOp = "assignGroups"')
    sp = container(f"cntSp_{s}", 0, 96, "Parent.Width", sections_h, [
        label(f"lblSpState_{s}", 'If(IsBlank(varApp.ServicePrincipalId), "This app has no enterprise application yet.", "This app already has an enterprise application.")',
              0, 0, "Parent.Width", 28, size=11, bold=True),
        field_label(f"lblSpAssign_{s}", "Assignment required", 0, 40, 300),
        toggle(f"tglAssign_{s}", "true", 0, 62),
        hint(f"hntSpAssign_{s}", q("Only users in an assigned group can sign in or get tokens. Recommended."), 0, 98, "Parent.Width"),
    ], Visible='varOp = "createSP"')

    detail = container(f"cntDetail_{s}", 376, 160, "Parent.Width - 416", "Parent.Height - 160 - 92", [
        label(f"lblAppTitle_{s}", "varApp.Title", 0, 0, "Parent.Width", 30, size=15, bold=True),
        hint(f"lblAppInfo_{s}", '"App ID " & varApp.AppId & "    ·    appCatID " & varApp.AppCatId & "    ·    Team " & Coalesce(varApp.TeamGroupName, "-")', 0, 32, "Parent.Width"),
        hint(f"lblAppInfo2_{s}", '"App ID URI: " & Coalesce(varApp.IdentifierUri, "not set") & "    ·    Enterprise app: " & If(IsBlank(varApp.ServicePrincipalId), "not created", "yes")', 0, 54, "Parent.Width"),
        rect(f"recDetailSep_{s}", 0, 84, "Parent.Width", 1, fill="gTheme.Border", thickness=0),
        expose, roles, assign, sp,
        field_label(f"lblJust_{s}", "Business justification", COL1_X, "Parent.Height - 140", COL_W, required=True),
        text_input(f"txtJust_{s}", '""', q("Why is this change needed?"), COL1_X, "Parent.Height - 118", COL_W, 72, multiline=True),
        field_label(f"lblTicket_{s}", "Change ticket", COL2_X, "Parent.Height - 140", COL_W),
        text_input(f"txtTicket_{s}", '""', q("Optional"), COL2_X, "Parent.Height - 118", COL_W),
    ], Visible="!IsBlank(varApp)")

    children = frame(s, title, sub, '"Home  ›  " & ' + title) + [
        rect(f"recApps_{s}", 24, 146, 320, "Parent.Height - 146 - 80"),
        label(f"lblAppsHead_{s}", q("Your applications"), 40, 156, 288, 26, size=12, bold=True),
        text_input(f"txtSearchApps_{s}", '""', q("Search by name or appCatID"), 40, 186, 288, 34),
        gallery(f"galApps_{s}",
                f'Filter(Sort(gMyApps, Title), IsBlank(txtSearchApps_{s}.Text) || StartsWith(Title, txtSearchApps_{s}.Text) || txtSearchApps_{s}.Text in AppCatId)',
                24, 228, 320, "Parent.Height - 228 - 88", 64,
                on_select="Set(varApp, ThisItem); Clear(colScopes); Clear(colRoles); Clear(colRoleGroups); Clear(colAssign)",
                children=[
                    rect(f"recAppSel_{s}", 0, 6, 4, 52, fill="If(varApp.ObjectId = ThisItem.ObjectId, gTheme.Primary, RGBA(0, 0, 0, 0))", thickness=0,
                         OnSelect="Select(Parent)"),
                    label(f"lblAppName_{s}", "ThisItem.Title", 16, 10, "Parent.TemplateWidth - 32", 24, bold=True, OnSelect="Select(Parent)"),
                    label(f"lblAppMeta_{s}", 'ThisItem.AppCatId & "  ·  " & Coalesce(ThisItem.TeamGroupName, "you are an owner")', 16, 34,
                          "Parent.TemplateWidth - 32", 20, size=9, color="gTheme.Muted", OnSelect="Select(Parent)"),
                ]),
        label(f"lblNoApps_{s}", q("No app registrations owned by your groups yet. The catalog refreshes every hour."),
              40, 236, 288, 60, size=10, color="gTheme.Muted", Wrap="true", Visible=f"CountRows(galApps_{s}.AllItems) = 0"),
        rect(f"recDetail_{s}", 360, 146, "Parent.Width - 384", "Parent.Height - 146 - 80"),
        label(f"lblPick_{s}", q("Choose one of your applications on the left."), 376, 170, 500, 30, size=11, color="gTheme.Muted",
              Visible="IsBlank(varApp)"),
        detail,
        rect(f"recCmd_{s}", 0, "Parent.Height - 64", "Parent.Width", 64),
        button(f"btnSubmit_{s}", q("Submit request"), submit, 360, "Parent.Height - 50", 170, 36, DisplayMode="If(IsBlank(varApp), DisplayMode.Disabled, DisplayMode.Edit)"),
        button(f"btnCancel_{s}", q("Cancel"), "Set(varResetChange, true); Navigate(scrHome, ScreenTransition.Fade)", 540, "Parent.Height - 50", 120, 36, kind="subtle"),
    ]
    write("scrAppChange", root(s, children), "Changes to an existing app: expose API, app roles, role assignments, enterprise app")


# ============================================================================ scrMyRequests
def my_requests() -> None:
    s = "My"
    sel = f"galReq_{s}.Selected"
    filt = (f'Filter(Sort(EntraRequests, ID, SortOrder.Descending), Switch(ddFilter_{s}.Selected.Value, '
            '"Open", Status.Value in ["Submitted", "PendingManagerApproval", "PendingEntraApproval", "Approved", "InProgress"], '
            '"Completed", Status.Value = "Completed", "Rejected / failed", Status.Value in ["Rejected", "Failed"], true))')

    def stage(i: int, title: str, state: str, fill: str) -> list:
        x = f"{i} * ((Parent.Width - 36) / 4 + 12)"
        w = "(Parent.Width - 36) / 4"
        return [
            rect(f"recStage{i}_{s}", x, 70, w, 72, fill=fill, border="gTheme.Border"),
            label(f"lblStage{i}T_{s}", q(title), f"{x} + 12", 78, f"{w} - 24", 24, size=10, bold=True),
            label(f"lblStage{i}S_{s}", state, f"{x} + 12", 102, f"{w} - 24", 36, size=9, color="gTheme.Muted", Wrap="true",
                  VerticalAlign="VerticalAlign.Top"),
        ]

    onboard = f'{sel}.RequestType.Value = "onboardGroup"'

    def decision_fill(col: str) -> str:
        return f'Switch({sel}.{col}.Value, "Approved", gTheme.SuccessLight, "Rejected", gTheme.DangerLight, gTheme.Card)'

    detail_html = f"""With({{r: ParseJSON(Coalesce({sel}.ResultJson, "{{}}"))}},
"<div style='font-family:Segoe UI, sans-serif; font-size:13px; color:#323130; line-height:1.5'>" &
"<table style='border-collapse:collapse; width:100%'>" &
"<tr><td style='color:#605e5c; width:180px; padding:3px 0'>Requested by</td><td>" & {sel}.'Created By'.DisplayName & "</td></tr>" &
"<tr><td style='color:#605e5c; padding:3px 0'>Justification</td><td>" & {sel}.Justification & "</td></tr>" &
If(!IsBlank({sel}.TicketReference), "<tr><td style='color:#605e5c; padding:3px 0'>Ticket</td><td>" & {sel}.TicketReference & "</td></tr>", "") &
If(!IsBlank({sel}.ManagerComment), "<tr><td style='color:#605e5c; padding:3px 0'>Manager comment</td><td>" & {sel}.ManagerComment & "</td></tr>", "") &
If(!IsBlank({sel}.EntraComment), "<tr><td style='color:#605e5c; padding:3px 0'>Entra team comment</td><td>" & {sel}.EntraComment & "</td></tr>", "") &
If(!IsBlank(Text(r.appId)), "<tr><td style='color:#605e5c; padding:3px 0'>Application (client) ID</td><td><b>" & Text(r.appId) & "</b></td></tr>", "") &
If(!IsBlank(Text(r.applicationObjectId)), "<tr><td style='color:#605e5c; padding:3px 0'>Object ID</td><td>" & Text(r.applicationObjectId) & "</td></tr>", "") &
If(!IsBlank(Text(r.identifierUri)), "<tr><td style='color:#605e5c; padding:3px 0'>Application ID URI</td><td>" & Text(r.identifierUri) & "</td></tr>", "") &
If(!IsBlank(Text(r.servicePrincipalId)), "<tr><td style='color:#605e5c; padding:3px 0'>Enterprise app</td><td>" & Text(r.servicePrincipalId) & "</td></tr>", "") &
If(!IsBlank(Text(r.groupId)), "<tr><td style='color:#605e5c; padding:3px 0'>Group</td><td>" & Text(r.groupId) & "</td></tr>", "") &
If(!IsBlank(Text(r.assignmentsText)), "<tr><td style='color:#605e5c; padding:3px 0'>Role assignments</td><td>" & Text(r.assignmentsText) & "</td></tr>", "") &
"</table>" &
If(!IsBlank({sel}.ErrorMessage), "<p style='margin-top:10px; padding:8px 12px; background:#fde7e9; border-left:3px solid #d13438'><b>Error</b><br>" & {sel}.ErrorMessage & "</p>", "") &
If(!IsBlank({sel}.RequestSummary), "<p style='margin-top:10px; color:#605e5c'><b>Summary sent to approvers</b><br>" & Substitute({sel}.RequestSummary, Char(10), "<br>") & "</p>", "") &
"</div>"
)"""
    detail = container(f"cntDetail_{s}", 476, 202, "Parent.Width - 516", "Parent.Height - 226", [
        label(f"lblDName_{s}", f"{sel}.TargetDisplayName", 0, 0, "Parent.Width - 170", 30, size=15, bold=True),
        status_badge(f"lblDStatus_{s}", f"{sel}.Status.Value", "Parent.Width - 160", 4, 160, 26),
        hint(f"lblDMeta_{s}", f'{sel}.Title & "   ·   " & {sel}.RequestType.Value & "   ·   appCatID " & {sel}.AppCatId & "   ·   " & Text({sel}.Created, "dd mmm yyyy hh:mm")',
             0, 34, "Parent.Width"),
        *stage(0, "1  Submitted", f'Text({sel}.Created, "dd mmm yyyy hh:mm")', "gTheme.SuccessLight"),
        *stage(1, "2  Manager approval", f'If({onboard}, "Not needed", {sel}.ManagerDecision.Value & If(!IsBlank({sel}.ManagerName), " · " & {sel}.ManagerName, ""))',
               f'If({onboard}, gTheme.Bg, {decision_fill("ManagerDecision")})'),
        *stage(2, "3  Entra ID team", f'If({onboard}, "Not needed", {sel}.EntraDecision.Value & If(!IsBlank({sel}.EntraDecisionBy), " · " & {sel}.EntraDecisionBy, ""))',
               f'If({onboard}, gTheme.Bg, {decision_fill("EntraDecision")})'),
        *stage(3, "4  Applied in Entra ID",
               f'Switch({sel}.Status.Value, "Completed", "Done · " & Text({sel}.CompletedAt, "dd mmm hh:mm"), "Failed", "Failed — see error", "InProgress", "Running…", "Not started")',
               f'Switch({sel}.Status.Value, "Completed", gTheme.SuccessLight, "Failed", gTheme.DangerLight, "InProgress", gTheme.PrimaryLight, gTheme.Card)'),
        html(f"htmlDetail_{s}", detail_html, 0, 156, "Parent.Width", "Parent.Height - 156 - 48"),
        button(f"btnOpenEntra_{s}", q("Open in Entra admin center"),
               f'Launch("https://entra.microsoft.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/Overview/appId/" & Text(ParseJSON(Coalesce({sel}.ResultJson, "{{}}")).appId))',
               0, "Parent.Height - 40", 230, 36, kind="secondary",
               Visible=f'!IsBlank(Text(ParseJSON(Coalesce({sel}.ResultJson, "{{}}")).appId))'),
    ], Visible=f"!IsBlank({sel}.ID)")

    children = frame(s, q("My requests"), q("Approvals happen in Outlook and Teams; this page shows where each request is and what was created."),
                     q("Home  ›  My requests")) + [
        dropdown(f"ddFilter_{s}", '["All", "Open", "Completed", "Rejected / failed"]', q("All"), 24, 150, 200, 34),
        button(f"btnRefresh_{s}", q("Refresh"), "Refresh(EntraRequests)", 234, 150, 110, 34, kind="subtle"),
        button(f"btnNew_{s}", q("＋ New request"), "Navigate(scrHome, ScreenTransition.Fade)", "Parent.Width - 184", 150, 160, 34),
        rect(f"recList_{s}", 24, 194, 420, "Parent.Height - 218"),
        gallery(f"galReq_{s}", filt, 24, 196, 420, "Parent.Height - 222", 78,
                Default="LookUp(EntraRequests, ID = varSelectedReqId)",
                children=[
                    rect(f"recReqSel_{s}", 0, 6, 4, 66, fill="If(ThisItem.IsSelected, gTheme.Primary, RGBA(0, 0, 0, 0))", thickness=0, OnSelect="Select(Parent)"),
                    label(f"lblReqName_{s}", "ThisItem.TargetDisplayName", 16, 8, "Parent.TemplateWidth - 180", 24, bold=True, OnSelect="Select(Parent)"),
                    label(f"lblReqMeta_{s}", 'ThisItem.Title & "  ·  " & ThisItem.RequestType.Value', 16, 32, "Parent.TemplateWidth - 32", 20, size=9,
                          color="gTheme.Muted", OnSelect="Select(Parent)"),
                    label(f"lblReqDate_{s}", 'Text(ThisItem.Created, "dd mmm yyyy hh:mm")', 16, 52, 200, 20, size=9, color="gTheme.Muted", OnSelect="Select(Parent)"),
                    status_badge(f"lblReqStatus_{s}", "ThisItem.Status.Value", "Parent.TemplateWidth - 160", 10, 146, 24),
                    rect(f"recReqSep_{s}", 12, 77, "Parent.TemplateWidth - 24", 1, fill="gTheme.Border", thickness=0),
                ]),
        label(f"lblNoReq_{s}", q("No requests match this filter."), 40, 210, 380, 30, size=10, color="gTheme.Muted",
              Visible=f"CountRows(galReq_{s}.AllItems) = 0"),
        rect(f"recDetailCard_{s}", 460, 194, "Parent.Width - 484", "Parent.Height - 218"),
        detail,
    ]
    write("scrMyRequests", root(s, children), "Request history: approval stages, results and errors")


if __name__ == "__main__":
    home()
    new_app()
    new_group()
    add_group()
    app_change()
    my_requests()
    print("generated:", ", ".join(sorted(p.name for p in OUT.glob("*.pa.yaml"))))
