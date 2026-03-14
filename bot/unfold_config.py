from django.utils.translation import gettext_lazy as _
from django.templatetags.static import static
from django.urls import reverse_lazy


def dashboard_callback(request, context):
    from bot.models import User, LiveSession, LiveParticipant
    from django.utils import timezone
    from django.db.models import Count
    from django.db.models.functions import TruncDate
    import datetime

    today = timezone.now().date()
    month_ago = today - datetime.timedelta(days=30)

    # === KPI Kartalar ===
    context["kpi_cards"] = [
        {
            "label": _("Jami foydalanuvchilar"),
            "value": User.objects.filter(is_staff=False).count(),
            "icon": "group",
            "color": "blue"
        },
        {
            "label": _("Bu oy qo'shilganlar"),
            "value": User.objects.filter(is_staff=False, date_joined__date__gte=month_ago).count(),
            "icon": "person_add",
            "color": "green"
        },
        {
            "label": _("Faol jonli efirlar"),
            "value": LiveSession.objects.filter(is_active=True).count(),
            "icon": "live_tv",
            "color": "orange"
        },
        {
            "label": _("Jami jonli efirlar"),
            "value": LiveSession.objects.count(),
            "icon": "video_library",
            "color": "purple"
        },
    ]

    # === Kunlik foydalanuvchilar o'sishi (so'nggi 30 kun) ===
    daily_data = (
        User.objects
        .filter(is_staff=False, date_joined__date__gte=month_ago)
        .annotate(day=TruncDate("date_joined"))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )

    # Barcha 30 kunni generatsiya qil (odam bo'lmagan kunlar = 0)
    all_days = {}
    for i in range(29, -1, -1):
        day = today - datetime.timedelta(days=i)
        all_days[day] = 0

    for e in daily_data:
        all_days[e["day"]] = e["count"]

    # Yangi foydalanuvchilar (kunlik)
    daily_new = [
        {"day": day.strftime("%d %b"), "count": count}
        for day, count in sorted(all_days.items())
    ]

    # Jami (cumulative)
    cumulative = 0
    base_count = User.objects.filter(
        is_staff=False,
        date_joined__date__lt=month_ago
    ).count()
    cumulative = base_count

    daily_total = []
    for day, count in sorted(all_days.items()):
        cumulative += count
        daily_total.append({"day": day.strftime("%d %b"), "count": cumulative})

    context["daily_new_users"] = daily_new
    context["daily_total_users"] = daily_total

    # Bugungi yangi foydalanuvchilar soni
    context["today_new_users"] = all_days.get(today, 0)

    # Jami foydalanuvchilar soni
    context["total_users_count"] = User.objects.filter(is_staff=False).count()

    # === Top 5 referalchilar ===
    context["top_referrers"] = (
        User.objects
        .filter(is_staff=False, referral_points__gt=0)
        .order_by("-referral_points")[:5]
    )

    # === Jonli efir statistikasi ===
    live_stats = (
        LiveSession.objects
        .annotate(participants=Count("liveparticipant"))
        .order_by("-started_at")[:3]
    )
    context["live_stats"] = live_stats

    # === So'nggi ro'yxatdan o'tganlar ===
    context["recent_users"] = (
        User.objects
        .filter(is_staff=False)
        .order_by("-date_joined")[:3]
    )

    return context


def environment_callback(request):
    from django.conf import settings
    return ["Development", "warning"] if settings.DEBUG else ["Production", "success"]


UNFOLD = {
    "SITE_TITLE": "KonkursBot | Administration",
    "SITE_HEADER": "KonkursBot",
    "SITE_SUBHEADER": "Telegram Bot",
    "SITE_URL": "/",
    "SITE_SYMBOL": "emoji_events",

    "DASHBOARD_CALLBACK": "bot.unfold_config.dashboard_callback",
    "ENVIRONMENT": "bot.unfold_config.environment_callback",

    "SHOW_HISTORY": False,
    "SHOW_VIEW_ON_SITE": True,
    "SHOW_BACK_BUTTON": True,

    "BORDER_RADIUS": "10px",

    "COLORS": {
        "primary": {
            "50":  "255 247 237",
            "100": "255 237 213",
            "200": "254 215 170",
            "300": "253 186 116",
            "400": "251 146 60",
            "500": "249 115 22",
            "600": "234 88 12",
            "700": "194 65 12",
            "800": "154 52 18",
            "900": "124 45 18",
            "950": "67 20 7",
        },
    },

    "ACTION_ROW_ALWAYS_VISIBLE": True,

    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": _("Bosh sahifa"),
                "separator": False,
                "collapsible": False,
                "items": [
                    {
                        "title": _("Dashboard"),
                        "icon": "dashboard",
                        "link": "/admin/",
                    },
                ],
            },
            {
                "title": _("Foydalanuvchilar"),
                "separator": True,
                "collapsible": False,
                "items": [
                    {
                        "title": _("Foydalanuvchilar"),
                        "icon": "person",
                        "link": reverse_lazy("admin:bot_user_changelist"),
                        "permission": lambda request: request.user.has_perm("bot.view_user"),
                    },
                ],
            },
            {
                "title": _("Jonli Efir"),
                "separator": True,
                "collapsible": False,
                "items": [
                    {
                        "title": _("Jonli efirlar"),
                        "icon": "live_tv",
                        "link": reverse_lazy("admin:bot_livesession_changelist"),
                        "permission": lambda request: request.user.has_perm("bot.view_livesession"),
                    },
                    {
                        "title": _("Ishtirokchilar"),
                        "icon": "groups",
                        "link": reverse_lazy("admin:bot_liveparticipant_changelist"),
                        "permission": lambda request: request.user.has_perm("bot.view_liveparticipant"),
                    },
                ],
            },
        ],
    },
}