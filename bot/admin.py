from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from unfold.contrib.filters.admin import RangeNumericListFilter
from .models import User, LiveSession, LiveParticipant


class ReferralPointsFilter(RangeNumericListFilter):
    parameter_name = 'referral_points'
    title = _("Ball oralig'i")


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    model = User
    request_cache = None
    _filtered_ids = []

    list_display = (
        'row_number', 'id', 'full_name_link', 'telegram_id', 'phone',
        'inviter', 'referral_points_display', 'is_staff_display', 'is_active_display',
    )

    ordering = ('-referral_points',)
    search_fields = ('username', 'full_name', 'telegram_id', 'phone')
    list_filter = ('is_staff', 'is_active', ReferralPointsFilter)
    list_filter_submit = True

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Shaxsiy ma\'lumotlar'), {'fields': ('full_name', 'telegram_id', 'phone')}),
        (_('Referral'), {'fields': ('inviter', 'referral_points')}),
        (_('Ruxsatlar'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Muhim sanalar'), {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'full_name', 'is_staff', 'is_superuser'),
        }),
    )

    readonly_fields = ('last_login', 'date_joined')
    actions = ['make_delete']

    def row_number(self, obj):
        try:
            return self._filtered_ids.index(obj.id) + 1
        except ValueError:
            return '-'
    row_number.short_description = _("№")

    def make_delete(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"✅ {count} ta foydalanuvchi o'chirildi")
    make_delete.short_description = "🗑 Tanlangan foydalanuvchilarni o'chirish"

    def full_name_link(self, obj):
        return format_html('<a href="{}">{}</a>', f'/admin/bot/user/{obj.id}/change/', obj.full_name or "-")
    full_name_link.short_description = _("Foydalanuvchi ismi")
    full_name_link.admin_order_field = 'full_name'

    def referral_points_display(self, obj):
        return obj.referral_points
    referral_points_display.short_description = _("Ball")
    referral_points_display.admin_order_field = 'referral_points'

    def is_staff_display(self, obj):
        return "🟢" if obj.is_staff else "🔴"
    is_staff_display.short_description = _("Staff")
    is_staff_display.admin_order_field = 'is_staff'

    def is_active_display(self, obj):
        return "🟢" if obj.is_active else "🔴"
    is_active_display.short_description = _("Faol")
    is_active_display.admin_order_field = 'is_active'

    def changelist_view(self, request, extra_context=None):
        self.request_cache = request
        extra_context = extra_context or {}
        response = super().changelist_view(request, extra_context=extra_context)
        try:
            cl = response.context_data['cl']
            self._filtered_ids = list(cl.queryset.values_list('id', flat=True))
        except (AttributeError, KeyError):
            self._filtered_ids = []
        return response


@admin.register(LiveSession)
class LiveSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'is_active', 'started_at')
    list_filter = ('is_active',)
    ordering = ('-started_at',)
    readonly_fields = ('started_at',)


@admin.register(LiveParticipant)
class LiveParticipantAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'live', 'joined_at')
    list_filter = ('live',)
    ordering = ('-joined_at',)
    readonly_fields = ('joined_at',)