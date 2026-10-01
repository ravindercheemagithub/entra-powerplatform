// ---------------------------------------------------------------------------
// App > OnStart. Paste all. Declares the working collections and variables
// with their shapes (Collect a sample record, then Clear) so every formula
// type-checks before the first click.
// ---------------------------------------------------------------------------
ClearCollect(colScopes, { Key: "", Value: "", Type: "User", AdminName: "", AdminDesc: "" });
Clear(colScopes);
ClearCollect(colRoles, { Key: "", Value: "", DisplayName: "", Description: "", Members: "Users/Groups" });
Clear(colRoles);
ClearCollect(colRoleGroups, { RoleKey: "", Mode: "", GroupId: "", DisplayName: "", Description: "", OwnerIds: "" });
Clear(colRoleGroups);
ClearCollect(colAssign, { RoleId: "", RoleValue: "", Mode: "", GroupId: "", DisplayName: "", Description: "", OwnerIds: "" });
Clear(colAssign);

Set(varNewTeam, { Mode: "", GroupId: "", DisplayName: "", Description: "", OwnerIds: "" });
Set(varAssignRole, { Id: "", Value: "" });
Set(varStep, 1);
Set(varMaxStep, 1);
Set(varOp, "exposeApi");
Set(varGroupMode, "standalone");
Set(varGroupForRole, "");
Set(varGroupSuggest, "grp-");
Set(varReqId, "");
Set(varSelectedReqId, Blank());
Set(varResetNewApp, true);
Set(varResetChange, true);
