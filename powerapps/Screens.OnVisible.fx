// ---------------------------------------------------------------------------
// Screen properties that are NOT part of the pasted YAML (paste code covers
// controls only). For each screen: select it in the Tree view, then set:
//   Fill      = gTheme.Bg
//   OnVisible = the formula below
// ---------------------------------------------------------------------------

// ===== scrHome.OnVisible
Refresh(EntraRequests)

// ===== scrNewApp.OnVisible
// Resets only when arriving from Home / after submit -- returning from the
// "Add an existing group" screen keeps everything that was typed.
Refresh(EntraCatalogGroups);
If(IsBlank(varStep), Set(varStep, 1); Set(varMaxStep, 1));
If(varResetNewApp,
    Set(varResetNewApp, false);
    Set(varStep, 1);
    Set(varMaxStep, 1);
    Set(varStepError, "");
    Clear(colScopes); Clear(colRoles); Clear(colRoleGroups);
    Reset(txtAppName_NewApp); Reset(txtAppCatId_NewApp); Reset(ddEnv_NewApp); Reset(txtBorShort_NewApp); Reset(cmbTeam_NewApp);
    Reset(txtJustification_NewApp); Reset(txtDescription_NewApp); Reset(ddPlatform_NewApp); Reset(txtRedirect_NewApp);
    Reset(chkExpose_NewApp); Reset(radUri_NewApp); Reset(txtCustomUri_NewApp);
    Reset(chkIdEmail_NewApp); Reset(chkIdUpn_NewApp); Reset(chkIdGiven_NewApp); Reset(chkIdFamily_NewApp);
    Reset(chkAtEmail_NewApp); Reset(chkAtUpn_NewApp); Reset(chkAtIdtyp_NewApp); Reset(ddGroupsClaim_NewApp);
    Reset(tglCreateSp_NewApp); Reset(tglAssign_NewApp); Reset(radAudience_NewApp); Reset(txtTags_NewApp); Reset(txtTicket_NewApp);
    // Clone: the fields above take their defaults from varClone; the scopes, roles and role groups come from its payload.
    If(!IsBlank(varClone),
        Set(varMaxStep, 5);
        With({j: ParseJSON(Coalesce(varClone.payload, "{}"))},
            ForAll(Table(j.exposeApi.scopes) As sc,
                Collect(colScopes, {Key: Text(GUID()), Value: Text(sc.Value.value), Type: Coalesce(Text(sc.Value.type), "User"),
                    AdminName: Text(sc.Value.adminConsentDisplayName), AdminDesc: Text(sc.Value.adminConsentDescription)}));
            ForAll(Table(j.appRoles) As r,
                With({k: Text(GUID())},
                    Collect(colRoles, {Key: k, Value: Text(r.Value.value), DisplayName: Text(r.Value.displayName), Description: Text(r.Value.description),
                        Members: Switch(Text(r.Value.allowedMemberTypes), "Application", "Applications", "User,Application", "Both", "Users/Groups")});
                    ForAll(Table(r.Value.assignGroups) As g,
                        Collect(colRoleGroups, {RoleKey: k, Mode: "existing", GroupId: Text(g.Value.id), DisplayName: Text(g.Value.displayName),
                            Description: "", OwnerIds: ""}))))
        )
    )
)

// ===== scrAddGroup.OnVisible
Refresh(EntraRequests); Refresh(EntraCatalogGroups)

// ===== scrAppChange.OnVisible
If(varResetChange,
    Set(varResetChange, false);
    Set(varApp, Blank());
    Clear(colScopes); Clear(colRoles); Clear(colRoleGroups); Clear(colAssign);
    Set(varLookupBusy, false);
    Reset(txtAppId_Change); Reset(txtAppCat_Change); Reset(radUri_Change); Reset(txtCustomUri_Change); Reset(ddRole_Change);
    Reset(cmbGroup_Change); Reset(tglAssign_Change); Reset(txtJust_Change); Reset(txtTicket_Change);
    // Clone: scopes, roles or assignments come from the copied payload; the user still has to click Search.
    If(!IsBlank(varCloneChange),
        With({j: ParseJSON(Coalesce(varCloneChange.payload, "{}"))},
            ForAll(Table(j.scopes) As sc,
                Collect(colScopes, {Key: Text(GUID()), Value: Text(sc.Value.value), Type: Coalesce(Text(sc.Value.type), "User"),
                    AdminName: Text(sc.Value.adminConsentDisplayName), AdminDesc: Text(sc.Value.adminConsentDescription)}));
            ForAll(Table(j.appRoles) As r,
                With({k: Text(GUID())},
                    Collect(colRoles, {Key: k, Value: Text(r.Value.value), DisplayName: Text(r.Value.displayName), Description: Text(r.Value.description),
                        Members: Switch(Text(r.Value.allowedMemberTypes), "Application", "Applications", "User,Application", "Both", "Users/Groups")});
                    ForAll(Table(r.Value.assignGroups) As g,
                        Collect(colRoleGroups, {RoleKey: k, Mode: "existing", GroupId: Text(g.Value.id), DisplayName: Text(g.Value.displayName),
                            Description: "", OwnerIds: ""}))));
            ForAll(Table(j.assignments) As a,
                Collect(colAssign, {RoleId: Text(a.Value.appRoleId), RoleValue: Text(a.Value.appRoleValue), Mode: "existing",
                    GroupId: Text(a.Value.id), DisplayName: Text(a.Value.displayName), Description: "", OwnerIds: ""}))
        )
    )
)

// ===== scrTagGroup.OnVisible
Refresh(EntraRequests)

// ===== scrMyRequests.OnVisible
Refresh(EntraRequests)
