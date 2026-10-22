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
    Clear(colScopes); Clear(colRoles); Clear(colRoleGroups); Clear(colPerms);
    Set(varMorePerms, false);
    Reset(txtAppName_NewApp); Reset(txtAppCatId_NewApp); Reset(ddEnv_NewApp); Reset(ddType_NewApp); Reset(txtBorShort_NewApp); Reset(cmbTeam_NewApp);
    Reset(txtJustification_NewApp); Reset(txtDescription_NewApp); Reset(ddPlatform_NewApp); Reset(txtRedirect_NewApp);
    Reset(chkExpose_NewApp); Reset(radUri_NewApp); Reset(txtCustomUri_NewApp);
    Reset(chkIdEmail_NewApp); Reset(chkIdUpn_NewApp); Reset(chkIdGiven_NewApp); Reset(chkIdFamily_NewApp);
    Reset(chkAtEmail_NewApp); Reset(chkAtUpn_NewApp); Reset(chkAtIdtyp_NewApp); Reset(ddGroupsClaim_NewApp);
    Reset(radAudience_NewApp); Reset(txtTags_NewApp); Reset(txtTicket_NewApp);
    Reset(chkPOpenid_NewApp); Reset(chkPEmail_NewApp); Reset(chkPProfile_NewApp); Reset(chkPUserRead_NewApp); Reset(chkPOffline_NewApp); Reset(txtPerm_NewApp);
    Reset(ddOwnerRole_NewApp); Reset(txtDefUser_NewApp); Reset(cmbDefGroup_NewApp);
    // Clone: the fields above take their defaults from varClone; the scopes, roles and role groups come from its payload.
    If(!IsBlank(varClone),
        Set(varMaxStep, 6);
        With({j: ParseJSON(Coalesce(varClone.payload, "{}"))},
            ForAll(Split(Coalesce(varClone.graphScopes, ""), ",") As p,
                If(!IsBlank(p.Value) && !(Lower(p.Value) in ["openid", "email", "profile", "user.read"]), Collect(colPerms, {Value: p.Value})));
            ForAll(Table(j.defaultAccess) As d,
                Collect(colRoleGroups, {RoleKey: "default", Mode: Coalesce(Text(d.Value.mode), "existing"), GroupId: Text(d.Value.id),
                    DisplayName: Text(d.Value.displayName), Description: "", OwnerIds: ""}));
            ForAll(Table(j.exposeApi.scopes) As sc,
                Collect(colScopes, {Key: Text(GUID()), Value: Text(sc.Value.value), Type: Coalesce(Text(sc.Value.type), "User"),
                    AdminName: Text(sc.Value.adminConsentDisplayName), AdminDesc: Text(sc.Value.adminConsentDescription)}));
            ForAll(Table(j.appRoles) As r,
                With({k: Text(GUID())},
                    Collect(colRoles, {Key: k, Value: Text(r.Value.value), DisplayName: Text(r.Value.displayName), Description: Text(r.Value.description),
                        Members: Switch(Text(r.Value.allowedMemberTypes), "Application", "Applications", "User,Application", "Both", "Users/Groups")});
                    ForAll(Table(r.Value.assignGroups) As g,
                        Collect(colRoleGroups, {RoleKey: k, Mode: Coalesce(Text(g.Value.mode), "existing"), GroupId: Text(g.Value.id), DisplayName: Text(g.Value.displayName),
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
    Reset(cmbGroup_Change); Reset(txtAssignUser_Change); Reset(txtJust_Change); Reset(txtTicket_Change);
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
                        Collect(colRoleGroups, {RoleKey: k, Mode: Coalesce(Text(g.Value.mode), "existing"), GroupId: Text(g.Value.id), DisplayName: Text(g.Value.displayName),
                            Description: "", OwnerIds: ""}))));
            ForAll(Table(j.assignments) As a,
                Collect(colAssign, {RoleId: Text(a.Value.appRoleId), RoleValue: Text(a.Value.appRoleValue), Mode: Coalesce(Text(a.Value.mode), "existing"),
                    GroupId: Text(a.Value.id), DisplayName: Text(a.Value.displayName), Description: "", OwnerIds: ""}))
        )
    )
)

// ===== scrTagGroup.OnVisible
Refresh(EntraRequests)

// ===== scrDeleteApp.OnVisible
Set(varDelBusy, false); Set(varDelMsg, ""); Set(varDelConfirm, false);
Reset(txtAppId_Delete); Reset(radDelAction_Delete); Reset(txtJust_Delete); Reset(txtTicket_Delete)

// ===== scrGrantAccess.OnVisible
Set(varAccBusy, false); Set(varAccMsg, "");
Reset(txtAppId_Grant); Reset(radWho_Grant); Reset(txtAccGroup_Grant); Reset(txtJust_Grant); Reset(txtTicket_Grant)

// ===== scrMyRequests.OnVisible
Refresh(EntraRequests)
