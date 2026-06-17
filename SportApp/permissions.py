from rest_framework.permissions import BasePermission


class IsAdminGroup(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.groups.filter(name='Admin').exists()
        )

class IsUserGroup(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.groups.filter(name__in=['User', 'Admin']).exists()
        )

class IsOwnerOrAdmin(BasePermission):

    def has_object_permission(self, request, view, obj):
        # Admin może wszystko
        if request.user.groups.filter(name='Admin').exists():
            return True

        # Właściciel może edytować/usuwać swoje
        return obj.user == request.user