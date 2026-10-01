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
// "Create new group" screen keeps everything that was typed.
If(varResetNewApp,
    Set(varResetNewApp, false);
    Set(varStep, 1);
    Set(varMaxStep, 1);
    Set(varNewTeam, { Mode: "", GroupId: "", DisplayName: "", Description: "", OwnerIds: "" });
    Clear(colScopes); Clear(colRoles); Clear(colRoleGroups);
    Reset(txtAppName_NewApp); Reset(txtAppCatId_NewApp); Reset(radAudience_NewApp); Reset(cmbTeam_NewApp);
    Reset(txtJustification_NewApp); Reset(txtDescription_NewApp); Reset(ddPlatform_NewApp); Reset(txtRedirect_NewApp);
    Reset(txtTicket_NewApp); Reset(chkExpose_NewApp); Reset(radUri_NewApp); Reset(txtCustomUri_NewApp);
    Reset(chkIdEmail_NewApp); Reset(chkIdUpn_NewApp); Reset(chkIdGiven_NewApp); Reset(chkIdFamily_NewApp);
    Reset(chkAtEmail_NewApp); Reset(chkAtUpn_NewApp); Reset(chkAtIdtyp_NewApp); Reset(ddGroupsClaim_NewApp);
    Reset(tglCreateSp_NewApp); Reset(tglAssign_NewApp); Reset(cmbOwners_NewApp); Reset(txtTags_NewApp)
)

// ===== scrNewGroup.OnVisible
Reset(txtGroupName_Group); Reset(txtGroupDesc_Group); Reset(txtGroupAppCat_Group);
Reset(cmbGroupOwners_Group); Reset(cmbGroupMembers_Group); Reset(txtGroupJust_Group)

// ===== scrAppChange.OnVisible
If(varResetChange,
    Set(varResetChange, false);
    Set(varApp, Blank());
    Clear(colScopes); Clear(colRoles); Clear(colRoleGroups); Clear(colAssign);
    Reset(txtSearchApps_Change); Reset(radUri_Change); Reset(txtCustomUri_Change); Reset(ddRole_Change);
    Reset(cmbGroup_Change); Reset(tglAssign_Change); Reset(txtJust_Change); Reset(txtTicket_Change)
)

// ===== scrMyRequests.OnVisible
Refresh(EntraRequests)
