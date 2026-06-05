import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROUTES = ROOT / "app" / "routes"
OUT = ROOT / "Desktop_Valuation_API.postman_collection.json"
PAGINATION = [
    ("page", "1", 0),
    ("limit", "50", 0),
    ("search", "", 1),
    ("is_active", "true", 1),
]
FOLDERS = {
    "app/routes/auth.py": "User Auth",
    "app/routes/valuation.py": "Valuation",
    "app/routes/subscription.py": "Subscription",
    "app/routes/payment.py": "Payment",
    "app/routes/inquiry.py": "Inquiry",
    "app/routes/user_feedback.py": "User Feedback",
    "app/routes/admin/auth.py": "Admin Auth",
    "app/routes/admin/users.py": "Admin Users",
    "app/routes/admin/subscription_plans.py": "Admin Subscription Plans",
    "app/routes/admin/user_subscriptions.py": "Admin User Subscriptions",
    "app/routes/admin/valuations.py": "Admin Valuations",
    "app/routes/admin/dashboard.py": "Admin Dashboard",
    "app/routes/admin/feedback.py": "Admin Feedback",
    "app/routes/admin/staff.py": "Admin Staff",
    "app/routes/admin/inquiries.py": "Admin Inquiries",
    "app/routes/admin/country.py": "Admin Country",
    "app/routes/admin/system_config.py": "Admin System Config",
}
ORDER = list(FOLDERS.values())
BODY = {
    "UserCreate": {
        "email": "user@example.com",
        "username": "johndoe",
        "mobile_number": "+971501234567",
        "password": "SecurePassword123!",
        "role": "INDIVIDUAL",
    },
    "UserLogin": {"email": "user@example.com", "password": "SecurePassword123!"},
    "GoogleLogin": {"id_token": "{{google_id_token}}"},
    "RefreshTokenRequest": {"refresh_token": "{{user_refresh_token}}"},
    "UserUpdate": {
        "username": "John Doe Updated",
        "email": "updated.user@example.com",
        "mobile_number": "+971509999999",
    },
    "ChangePassword": {
        "old_password": "SecurePassword123!",
        "new_password": "NewSecurePassword123!",
        "confirm_password": "NewSecurePassword123!",
    },
    "ForgotPassword": {"email": "user@example.com"},
    "ResetPassword": {
        "token": "{{reset_token}}",
        "new_password": "ResetPassword123!",
        "confirm_password": "ResetPassword123!",
    },
    "ResendVerificationRequest": {"email": "user@example.com"},
    "AdminLogin": {"email": "admin@example.com", "password": "AdminPassword123!"},
    "AdminCreateUser": {
        "username": "newuser",
        "email": "new.user@example.com",
        "mobile_number": "+971500000001",
        "password": "SecurePassword123!",
        "role": "INDIVIDUAL",
        "is_superuser": False,
    },
    "AdminUserUpdate": {
        "username": "updateduser",
        "email": "updated.user@example.com",
        "mobile_number": "+971500000002",
        "role": "INDIVIDUAL",
    },
    "AdminResetPassword": {
        "new_password": "AdminReset123!",
        "confirm_password": "AdminReset123!",
    },
    "AdminFeedbackAction": {
        "status": "IN_PROGRESS",
        "reply": "We are reviewing your feedback.",
        "notify_user": True,
        "admin_note": "Handled by support team.",
    },
    "FeedbackCreate": {
        "type": "VALUATION",
        "subject": "Valuation review request",
        "message": "Please review the latest valuation outcome.",
        "rating": 5,
        "valuation_id": "{{valuation_id}}",
        "subscription_id": "{{subscription_id}}",
    },
    "FeedbackUpdate": {
        "subject": "Updated feedback subject",
        "message": "Sharing updated feedback details.",
        "rating": 4,
    },
    "FeedbackMessageCreate": {"message": "Following up on the previous discussion."},
    "InquiryCreate": {
        "type": "CONTACT",
        "first_name": "John",
        "last_name": "Doe",
        "email": "user@example.com",
        "phone_number": "+971501234567",
        "message": "I would like to know more about your valuation service.",
        "services": ["valuation", "consulting"],
    },
    "StaffCreate": {
        "name": "Support Manager",
        "email": "staff@example.com",
        "phone": "+971500000003",
        "password": "StaffPassword123!",
        "role": "support",
        "can_access_user": True,
        "can_access_staff": True,
        "can_access_dashboard": True,
        "can_access_reports": True,
        "can_access_subscriptions_plans": True,
        "can_access_config": True,
    },
    "StaffUpdate": {
        "name": "Updated Support Manager",
        "email": "updated.staff@example.com",
        "phone": "+971500000004",
        "password": "UpdatedStaff123!",
        "role": "support",
        "can_access_user": True,
        "can_access_staff": True,
        "can_access_dashboard": True,
        "can_access_reports": True,
        "can_access_subscriptions_plans": True,
        "can_access_config": True,
    },
    "SubscriptionPlanCreate": {
        "name": "PRO",
        "country_code": "AE",
        "price": 999,
        "currency": "AED",
        "max_reports": 25,
    },
    "SubscriptionPlanUpdate": {
        "name": "PRO PLUS",
        "price": 1299,
        "currency": "AED",
        "max_reports": 40,
    },
    "AssignSubscription": {
        "plan_id": "{{plan_id}}",
        "duration_days": 30,
        "pricing_country_code": "AE",
    },
    "UpdateSubscription": {
        "extend_days": 30,
        "reset_reports_used": False,
        "deactivate": False,
    },
    "UpdateSubscriptionDuration": {"duration_days": 365},
    "SystemConfigCreate": {
        "config_key": "SUPPORT_EMAIL",
        "config_value": "support@example.com",
        "description": "Primary support inbox.",
    },
    "SystemConfigUpdate": {
        "config_value": "helpdesk@example.com",
        "description": "Updated support inbox.",
    },
    "dict": {
        "razorpay_order_id": "{{razorpay_order_id}}",
        "razorpay_payment_id": "{{razorpay_payment_id}}",
        "razorpay_signature": "{{razorpay_signature}}",
    },
}
FORM = {
    "country": "United Arab Emirates",
    "full_address": "Yas Island, Abu Dhabi, UAE",
    "property_type": "apartment",
    "land_area": "1500 sqft",
    "built_up_area": "1250 sqft",
    "year_built": "2020",
    "ownership_type": "freehold",
    "configuration": "2BR + maid",
    "construction_status": "completed",
    "estimated_market_value": "1850000",
    "stories": "15",
    "purpose_of_valuation": "sale",
    "full_name": "John Doe",
    "client_name": "Miral",
    "project_name": "Water's Edge",
    "email": "user@example.com",
    "contact_number": "+971501234567",
}
Q = {
    "address": "Yas Island, Abu Dhabi, UAE",
    "category": "apartment",
    "country_code": "AE",
    "created_from": "2026-01-01T00:00:00Z",
    "created_to": "2026-12-31T23:59:59Z",
    "currency": "AED",
    "from_date": "2026-01-01T00:00:00Z",
    "to_date": "2026-12-31T23:59:59Z",
    "is_active": "true",
    "is_expired": "false",
    "order": "desc",
    "page": "1",
    "limit": "50",
    "payment_status": "PAID",
    "pricing_country_code": "AE",
    "plan_country_code": "AE",
    "search": "",
    "sort_by": "created_at",
    "start_from": "2026-01-01T00:00:00Z",
    "start_to": "2026-12-31T23:59:59Z",
    "status": "OPEN",
    "type": "GENERAL",
    "user_id": "{{user_id}}",
    "plan_id": "{{plan_id}}",
    "subscription_id": "{{subscription_id}}",
    "feedback_id": "{{feedback_id}}",
    "staff_id": "{{staff_id}}",
    "config_id": "{{config_id}}",
    "valuation_id": "{{valuation_id}}",
    "job_id": "{{job_id}}",
    "country": "United Arab Emirates",
    "verified_from": "2026-01-01T00:00:00Z",
    "verified_to": "2026-12-31T23:59:59Z",
    "verified_within_days": "30",
}


def t(x):
    return ast.unparse(x) if x else ""


def norm(x):
    return (
        x.replace("schemas.", "")
        .replace("Optional[", "")
        .replace("]", "")
        .replace(" | None", "")
        .replace("None | ", "")
    )


def title(s):
    return " ".join(p.capitalize() for p in re.split(r"[_/\\\\-]+", s) if p)


def auth(tok):
    return {
        "type": "bearer",
        "bearer": [{"key": "token", "value": "{{%s}}" % tok, "type": "string"}],
    }


def url(path, query=None):
    path = re.sub(r"{([^}]+)}", r"{{\1}}", path)
    raw = "{{base_url}}" + path
    if query:
        live = [i for i in query if not i.get("disabled")]
        if live:
            raw += "?" + "&".join(f"{i['key']}={i['value']}" for i in live)
    u = {
        "raw": raw,
        "host": ["{{base_url}}"],
        "path": [p for p in path.strip("/").split("/") if p],
    }
    if query:
        u["query"] = query
    return u


def qitem(k, v, d=False):
    return {"key": k, "value": str(v), **({"disabled": True} if d else {})}


def folder(path):
    return FOLDERS.get(path, title(Path(path).stem))


def parse_filters(tree):
    out = {}
    for n in tree.body:
        if isinstance(n, ast.ClassDef):
            init = next(
                (
                    c
                    for c in n.body
                    if isinstance(c, ast.FunctionDef) and c.name == "__init__"
                ),
                None,
            )
            if not init:
                continue
            args, defs, off = (
                init.args.args[1:],
                init.args.defaults,
                len(init.args.args[1:]) - len(init.args.defaults),
            )
            out[n.name] = [
                (
                    a.arg,
                    norm(t(a.annotation)),
                    i >= off and "Query(" in t(defs[i - off]),
                )
                for i, a in enumerate(args)
            ]
    return out


def query_val(name, typ):
    if name in Q:
        return Q[name]
    if typ == "bool":
        return "true"
    if name == "token":
        return "{{verification_token}}"
    if name.endswith("_id") or name == "id":
        return "{{%s}}" % name
    if "email" in name:
        return "user@example.com"
    if "phone" in name or "mobile" in name or "contact" in name:
        return "+971501234567"
    if "date" in name or "time" in name:
        return "2026-01-01T00:00:00Z"
    if typ in {"int", "float"}:
        return "1"
    return "sample"


def dedupe(qs):
    seen, out = set(), []
    for q in qs:
        if q["key"] in seen:
            continue
        seen.add(q["key"])
        out.append(q)
    return out


def item(name, method, path, desc, auth_obj=None, body=None, query=None):
    req = {"method": method, "header": [], "url": url(path, query), "description": desc}
    if auth_obj:
        req["auth"] = auth_obj
    if body and body["mode"] == "raw":
        req["header"] = [{"key": "Content-Type", "value": "application/json"}]
    if body:
        req["body"] = body
    return {"name": title(name), "request": req, "response": []}


def endpoints():
    out = []
    for fp in sorted(ROUTES.rglob("*.py")):
        if fp.name == "__init__.py":
            continue
        rel, tree, prefix = (
            fp.relative_to(ROOT).as_posix(),
            ast.parse(fp.read_text(encoding="utf-8")),
            "",
        )
        filters = parse_filters(tree)
        for n in tree.body:
            if (
                isinstance(n, ast.Assign)
                and any(
                    isinstance(tg, ast.Name) and tg.id == "router" for tg in n.targets
                )
                and isinstance(n.value, ast.Call)
                and t(n.value.func) == "APIRouter"
            ):
                for kw in n.value.keywords:
                    if kw.arg == "prefix" and isinstance(kw.value, ast.Constant):
                        prefix = kw.value.value
        for fn in tree.body:
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for dec in fn.decorator_list:
                if (
                    not isinstance(dec, ast.Call)
                    or not isinstance(dec.func, ast.Attribute)
                    or t(dec.func.value) != "router"
                    or dec.func.attr not in {"get", "post", "put", "patch", "delete"}
                ):
                    continue
                path = prefix + (
                    dec.args[0].value
                    if dec.args and isinstance(dec.args[0], ast.Constant)
                    else ""
                )
                args, defs, off = (
                    fn.args.args,
                    fn.args.defaults,
                    len(fn.args.args) - len(fn.args.defaults),
                )
                e = {
                    "folder": folder(rel),
                    "file": rel,
                    "name": fn.name,
                    "method": dec.func.attr.upper(),
                    "path": path,
                    "auth": None,
                    "q": [],
                    "json": None,
                    "form": [],
                    "files": [],
                }
                pnames = set(re.findall(r"{([^}]+)}", path))
                for i, a in enumerate(args):
                    d, ann, raw = (
                        defs[i - off] if i >= off else None,
                        norm(t(a.annotation)),
                        t(a.annotation),
                    )
                    dr = t(d)
                    if "require_management" in dr:
                        e["auth"] = "admin"
                    elif (
                        "get_current_user" in dr
                        and "optional" not in dr
                        and e["auth"] != "admin"
                    ):
                        e["auth"] = "user"
                    if (
                        a.arg
                        in {
                            "self",
                            "db",
                            "request",
                            "background_tasks",
                            "current_user",
                            "current_admin",
                            "admin_user",
                            "current",
                            "_",
                        }
                        or a.arg in pnames
                    ):
                        continue
                    if "pagination_params" in dr:
                        e["q"] += [qitem(*x[:2], bool(x[2])) for x in PAGINATION]
                        continue
                    if dr.startswith("Depends(") and ann in filters:
                        e["q"] += [
                            qitem(nm, query_val(nm, tp), opt)
                            for nm, tp, opt in filters[ann]
                        ]
                        continue
                    if ann == "UploadFile" or dr.startswith("File("):
                        e["files"].append(a.arg)
                        continue
                    if "desktop_valuation_form_dep" in dr:
                        e["form"] += [(k, v, 0) for k, v in FORM.items()]
                        continue
                    if dr.startswith("Form("):
                        e["form"].append(
                            (
                                a.arg,
                                query_val(a.arg, ann),
                                int(
                                    "None" in dr
                                    or "Optional[" in raw
                                    or "| None" in raw
                                ),
                            )
                        )
                        continue
                    if e["method"] == "GET" or dr.startswith("Query("):
                        e["q"].append(
                            qitem(
                                a.arg,
                                query_val(a.arg, ann),
                                "None" in dr or "Optional[" in raw or "| None" in raw,
                            )
                        )
                        continue
                    if ann in BODY or ann == "dict":
                        e["json"] = ann if ann in BODY else "dict"
                e["q"] = dedupe(e["q"])
                out.append(e)
    return out


def build():
    groups = {}
    for e in endpoints():
        desc = f"{('Public' if not e['auth'] else e['auth'].capitalize() + '-authenticated')} route from `{e['file']}::{e['name']}`. URL: `{e['method']} {e['path']}`."
        body = None
        if e["json"]:
            body = {
                "mode": "raw",
                "raw": json.dumps(BODY[e["json"]], indent=2),
                "options": {"raw": {"language": "json"}},
            }
        elif e["form"] or e["files"]:
            f = [
                {
                    "key": k,
                    "value": str(v),
                    "type": "text",
                    **({"disabled": True} if d else {}),
                }
                for k, v, d in e["form"]
            ]
            for name in e["files"]:
                src = (
                    "{{valuation_attachment_path}}"
                    if name == "attachment"
                    else (
                        "{{report_pdf_path}}"
                        if name == "pdf"
                        else "{{excel_file_path}}"
                        if name == "file"
                        else "{{%s_path}}" % name
                    )
                )
                f.append({"key": name, "type": "file", "src": src})
            body = {"mode": "formdata", "formdata": f}
        auth_obj = (
            auth("admin_access_token")
            if e["auth"] == "admin"
            else auth("user_access_token")
            if e["auth"] == "user"
            else None
        )
        groups.setdefault(e["folder"], []).append(
            item(
                e["name"], e["method"], e["path"], desc, auth_obj, body, e["q"] or None
            )
        )
    items = [{"name": k, "item": groups[k]} for k in ORDER if k in groups] + [
        {"name": k, "item": groups[k]} for k in sorted(groups) if k not in ORDER
    ]
    return {
        "info": {
            "name": "Desktop Valuation API",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "item": items,
        "variable": [
            {"key": k, "value": ""}
            for k in [
                "base_url",
                "user_access_token",
                "user_refresh_token",
                "admin_access_token",
                "verification_token",
                "reset_token",
                "google_id_token",
                "job_id",
                "valuation_id",
                "user_id",
                "country_id",
                "plan_id",
                "subscription_id",
                "feedback_id",
                "staff_id",
                "config_id",
                "razorpay_order_id",
                "razorpay_payment_id",
                "razorpay_signature",
                "valuation_attachment_path",
                "report_pdf_path",
                "excel_file_path",
            ]
        ],
    }


if __name__ == "__main__":
    c = build()
    for v in c["variable"]:
        if v["key"] == "base_url":
            v["value"] = "http://localhost:8000"
    OUT.write_text(json.dumps(c, indent=2), encoding="utf-8")
    print(f"Wrote {OUT} with {sum(len(g['item']) for g in c['item'])} requests.")
