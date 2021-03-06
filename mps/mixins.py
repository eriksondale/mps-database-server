# TODO PLEASE AVOID WILDCARD IMPORTS
from mps.templatetags.custom_filters import has_group, is_group_viewer, is_group_editor, is_group_admin
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.decorators import method_decorator
from django.template import loader
from django.http import HttpResponseForbidden
from assays.models import AssayRun, AssayRunStakeholder, AssayStudy, AssayStudyStakeholder
from mps.templatetags.custom_filters import filter_groups, VIEWER_SUFFIX, ADMIN_SUFFIX


# Unsemantic! Breaks PEP!
def PermissionDenied(request, message):
    """This function will take a string a render 403.html with that string as context"""
    template = loader.get_template('403.html')
    context = {
        'message': message
    }
    return HttpResponseForbidden(template.render(context, request))

# def check_if_user_is_active(user):
#     if not user or not user.is_active:
#         return PermissionDenied(
#             self.request,
#             'Your account is not currently active<br>'
#             'If you have recently registered, be sure to check your email for the activation link<br>'
#             'If you suspect this is an error, please contact an administrator'
#         )
#     else:
#         return None


def user_is_active(user):
    """Checks whether the user is active"""
    return user.is_active


def user_is_valid_study_viewer(user, study):
    # Find whether valid viewer by checking group and iterating over all access_groups
    valid_viewer = is_group_viewer(user, study.group.name)

    # Only check access groups if the study IS signed off on
    if not valid_viewer and study.signed_off_by:
        user_group_names = user.groups.all().values_list('name', flat=True)

        # Check if user is a stakeholder
        stakeholders = AssayStudyStakeholder.objects.filter(
            study=study
        ).prefetch_related(
            'study',
            'group',
            'signed_off_by'
        )
        stakeholder_group_names = {name: True for name in stakeholders.values_list('group__name', flat=True)}
        for group_name in user_group_names:
            if group_name.replace(VIEWER_SUFFIX, '').replace(ADMIN_SUFFIX, '') in stakeholder_group_names:
                valid_viewer = True
                # Only iterate as many times as is needed
                return valid_viewer

        # It not, check if all stake holders have signed off
        all_required_stakeholders_have_signed_off = stakeholders.filter(
            sign_off_required=True,
            signed_off_by_id=None
        ).count() == 0

        # Check if user needs to be checked for access groups
        if all_required_stakeholders_have_signed_off:
            access_group_names = {name: True for name in study.access_groups.all().values_list('name', flat=True)}

            for group_name in user_group_names:
                if group_name.replace(VIEWER_SUFFIX, '').replace(ADMIN_SUFFIX, '') in access_group_names:
                    valid_viewer = True
                    # Only iterate as many times as is needed
                    return valid_viewer

            # FINALLY: Check if the study is unrestricted
            if not study.restricted:
                valid_viewer = True
                return valid_viewer

    return valid_viewer


# DEPRECATED
def check_if_user_is_valid_study_viewer(user, study):
    # Find whether valid viewer by checking group and iterating over all access_groups
    valid_viewer = is_group_viewer(user, study.group.name)

    # Only check access groups if the study IS signed off on
    if not valid_viewer and study.signed_off_by:
        user_group_names = user.groups.all().values_list('name', flat=True)

        # Check if user is a stakeholder
        stakeholders = AssayRunStakeholder.objects.filter(
            study=study
        ).prefetch_related(
            'study',
            'group',
            'signed_off_by'
        )
        stakeholder_group_names = {name: True for name in stakeholders.values_list('group__name', flat=True)}
        for group_name in user_group_names:
            if group_name.replace(VIEWER_SUFFIX, '').replace(ADMIN_SUFFIX, '') in stakeholder_group_names:
                valid_viewer = True
                # Only iterate as many times as is needed
                return valid_viewer

        # It not, check if all stake holders have signed off
        all_required_stakeholders_have_signed_off = stakeholders.filter(
            sign_off_required=True,
            signed_off_by_id=None
        ).count() == 0

        # Check if user needs to be checked for access groups
        if all_required_stakeholders_have_signed_off:
            access_group_names = {name: True for name in study.access_groups.all().values_list('name', flat=True)}

            for group_name in user_group_names:
                if group_name.replace(VIEWER_SUFFIX, '').replace(ADMIN_SUFFIX, '') in access_group_names:
                    valid_viewer = True
                    # Only iterate as many times as is needed
                    return valid_viewer

            # FINALLY: Check if the study is unrestricted
            if not study.restricted:
                valid_viewer = True
                return valid_viewer

    return valid_viewer


# Add this mixin via multiple-inheritance and you need not change the dispatch every time
class LoginRequiredMixin(object):
    """This mixin requires the user to log in before continuing"""
    @method_decorator(login_required)
    @method_decorator(user_passes_test(user_is_active))
    def dispatch(self, *args, **kwargs):
        return super(LoginRequiredMixin, self).dispatch(*args, **kwargs)


class OneGroupRequiredMixin(object):
    """This mixin requires the user to have at least one group"""
    @method_decorator(login_required)
    @method_decorator(user_passes_test(user_is_active))
    def dispatch(self, *args, **kwargs):
        # if self.request.user.groups.all().count() == 0:
        #     return PermissionDenied(self.request, 'You must be a member of at least one group')
        valid_groups = filter_groups(self.request.user)
        if not valid_groups:
            return PermissionDenied(self.request, 'You must be a member of at least one group')
        return super(OneGroupRequiredMixin, self).dispatch(*args, **kwargs)


class ObjectGroupRequiredMixin(object):
    """This mixin requires group matching object's bound group"""
    @method_decorator(login_required)
    @method_decorator(user_passes_test(user_is_active))
    def dispatch(self, *args, **kwargs):
        self.object = self.get_object()
        if not is_group_editor(self.request.user, self.object.group.name):
            return PermissionDenied(self.request, 'You must be a member of the group ' + str(self.object.group))
        if self.object.signed_off_by:
            return PermissionDenied(
                self.request,
                'You cannot edit this because it has been signed off on by {0} {1}.'
                ' If something needs to be changed, contact the individual who signed off.'
                ' If you are the individual who signed off, please contact a database administrator.'.format(
                    self.object.signed_off_by.first_name,
                    self.object.signed_off_by.last_name
                )
            )
        return super(ObjectGroupRequiredMixin, self).dispatch(*args, **kwargs)


# CLONING IS NOT CURRENTLY AVAILABLE
# It is ostensibly possible to jam the user's status here so that it need not be acquired again
class StudyGroupMixin(object):
    """This mixin requires the user to have the group matching the study's group

    Attributes:
    detail - indicates that a detail page was initially requested
    update_redirect_url - where to to redirect in the case of detail redirect
    """
    detail = False
    # Default value for url to redirect to
    update_redirect_url = 'update/'

    @method_decorator(login_required)
    @method_decorator(user_passes_test(user_is_active))
    def dispatch(self, *args, **kwargs):
        # This is for adding study components
        if self.kwargs.get('study_id', ''):
            study = get_object_or_404(AssayStudy, pk=self.kwargs['study_id'])

            if not is_group_editor(self.request.user, study.group.name):
                return PermissionDenied(self.request, 'You must be a member of the group ' + str(study.group))

            if study.signed_off_by:
                return PermissionDenied(
                    self.request,
                    'You cannot add this because the study has been signed off on by {0} {1}.'
                    ' If something needs to be changed, contact the individual who signed off.'
                    ' If you are the individual who signed off, please contact a database administrator.'.format(
                        study.signed_off_by.first_name,
                        study.signed_off_by.last_name
                    )
                )

        else:
            try:
                current_object = self.get_object()
            except:
                # Evil except here!
                return PermissionDenied(self.request, 'An error has occurred.')

            study = current_object.study

            # Group editors can always see
            if is_group_editor(self.request.user, study.group.name) and not study.signed_off_by:
                # Redirects either to url + update or the specified url + object ID (as an attribute)
                # This is a little tricky if you don't look for {} in update_redirect_url
                if self.detail:
                    return redirect(self.update_redirect_url.format(current_object.id))
                else:
                    return super(StudyGroupMixin, self).dispatch(*args, **kwargs)

            valid_viewer = user_is_valid_study_viewer(self.request.user, study)

            # If the object is not restricted and the user is NOT a listed viewer
            # if study.restricted and not valid_viewer:
            if not valid_viewer:
                return PermissionDenied(self.request, 'You must be a member of the group ' + str(study.group))

            if study.signed_off_by and not self.detail:
                return PermissionDenied(
                    self.request,
                    'You cannot modify this because the study has been signed off on by {0} {1}.'
                    ' If something needs to be changed, contact the individual who signed off.'
                    ' If you are the individual who signed off, please contact a database administrator.'.format(
                        study.signed_off_by.first_name,
                        study.signed_off_by.last_name
                    )
                )

            # Otherwise return the detail view
            if self.detail:
                return super(StudyGroupMixin, self).dispatch(*args, **kwargs)
            else:
                return PermissionDenied(self.request, 'You do not have permission to edit this.')

        return super(StudyGroupMixin, self).dispatch(*args, **kwargs)


# DEPRECATED
# It is ostensibly possible to jam the user's status here so that it need not be acquired again
class StudyGroupRequiredMixin(object):
    """This mixin requires the user to have the group matching the study's group

    Attributes:
    cloning_permitted - Specifies whether cloning is permitted
    detail - indicates that a detail page was initially requested
    update_redirect_url - where to to redirect in the case of detail redirect
    """
    # Default value for whether or not cloning is permitted
    cloning_permitted = False
    detail = False
    # Default value for url to redirect to
    update_redirect_url = 'update/'

    @method_decorator(login_required)
    @method_decorator(user_passes_test(user_is_active))
    def dispatch(self, *args, **kwargs):
        # This is for adding study components
        if self.kwargs.get('study_id', ''):
            study = get_object_or_404(AssayRun, pk=self.kwargs['study_id'])

            if not is_group_editor(self.request.user, study.group.name):
                return PermissionDenied(self.request, 'You must be a member of the group ' + str(study.group))

            if study.signed_off_by:
                return PermissionDenied(
                    self.request,
                    'You cannot add this because the study has been signed off on by {0} {1}.'
                    ' If something needs to be changed, contact the individual who signed off.'
                    ' If you are the individual who signed off, please contact a database administrator.'.format(
                        study.signed_off_by.first_name,
                        study.signed_off_by.last_name
                    )
                )

            if self.cloning_permitted and self.request.GET.get('clone', ''):
                clone = get_object_or_404(self.model, pk=self.request.GET.get('clone', ''))
                if not is_group_editor(self.request.user, clone.group.name):
                    return PermissionDenied(
                        self.request,
                        'You must be a member of the group ' + str(clone.group) + ' to clone this'
                    )
        else:
            try:
                current_object = self.get_object()
            except:
                # Evil except here!
                return PermissionDenied(self.request, 'An error has occurred.')

            current_type = str(type(current_object))
            if current_type == "<class 'assays.models.AssayChipSetup'>":
                study = current_object.assay_run_id
            elif current_type == "<class 'assays.models.AssayPlateSetup'>":
                study = current_object.assay_run_id
            elif current_type == "<class 'assays.models.AssayChipReadout'>":
                study = current_object.chip_setup.assay_run_id
            elif current_type == "<class 'assays.models.AssayPlateReadout'>":
                study = current_object.setup.assay_run_id
            elif current_type == "<class 'assays.models.AssayChipTestResult'>":
                study = current_object.chip_readout.chip_setup.assay_run_id
            elif current_type == "<class 'assays.models.AssayPlateTestResult'>":
                study = current_object.readout.setup.assay_run_id

            # Group editors can always see
            if is_group_editor(self.request.user, study.group.name) and not study.signed_off_by:
                # Redirects either to url + update or the specified url + object ID (as an attribute)
                # This is a little tricky if you don't look for {} in update_redirect_url
                if self.detail:
                    return redirect(self.update_redirect_url.format(current_object.id))
                else:
                    return super(StudyGroupRequiredMixin, self).dispatch(*args, **kwargs)

            valid_viewer = check_if_user_is_valid_study_viewer(self.request.user, study)

            # If the object is not restricted and the user is NOT a listed viewer
            # if study.restricted and not valid_viewer:
            if not valid_viewer:
                return PermissionDenied(self.request, 'You must be a member of the group ' + str(study.group))

            if study.signed_off_by and not self.detail:
                return PermissionDenied(
                    self.request,
                    'You cannot modify this because the study has been signed off on by {0} {1}.'
                    ' If something needs to be changed, contact the individual who signed off.'
                    ' If you are the individual who signed off, please contact a database administrator.'.format(
                        study.signed_off_by.first_name,
                        study.signed_off_by.last_name
                    )
                )

            # Otherwise return the detail view
            if self.detail:
                return super(StudyGroupRequiredMixin, self).dispatch(*args, **kwargs)
            else:
                return PermissionDenied(self.request, 'You do not have permission to edit this.')

        return super(StudyGroupRequiredMixin, self).dispatch(*args, **kwargs)


# Deprecated
class ViewershipMixin(object):
    """This mixin checks if the user has the group neccessary to at least view the entry
    
    Attributes:
    study - specifies what study to look to for permissions
    """
    # Default study as None
    study = None

    @method_decorator(login_required)
    @method_decorator(user_passes_test(user_is_active))
    def dispatch(self, *args, **kwargs):
        self.object = self.get_object()
        if self.study.access == 'editors' and not has_group(self.request.user, self.study.group.name):
            return PermissionDenied(
                self.request,
                'You do not have editor permissions for the group ' + str(self.study.group)
            )
        elif not self.study.access == 'public' and not is_group_viewer(self.request.user, self.study.group.name):
            return PermissionDenied(
                self.request,
                'You do not have viewer permissions for the group ' + str(self.study.group)
            )
        # Otherwise return the detail view
        return super(ViewershipMixin, self).dispatch(*args, **kwargs)


class StudyViewershipMixin(object):
    """This mixin determines whether a user can view the study and its data"""
    @method_decorator(login_required)
    @method_decorator(user_passes_test(user_is_active))
    def dispatch(self, *args, **kwargs):
        self.object = self.get_object()

        valid_viewer = check_if_user_is_valid_study_viewer(self.request.user, self.object)
        # If the object is not restricted and the user is NOT a listed viewer, deny permission
        # if self.object.restricted and not valid_viewer:
        if not valid_viewer:
            return PermissionDenied(self.request, 'You must be a member of the group ' + str(self.object.group))
        # Otherwise return the detail view
        return super(StudyViewershipMixin, self).dispatch(*args, **kwargs)


class StudyViewerMixin(object):
    """This mixin determines whether a user can view the study and its data"""

    @method_decorator(login_required)
    @method_decorator(user_passes_test(user_is_active))
    def dispatch(self, *args, **kwargs):
        # Get the study
        study = get_object_or_404(AssayStudy, pk=self.kwargs['pk'])

        valid_viewer = user_is_valid_study_viewer(self.request.user, study)
        # If the object is not restricted and the user is NOT a listed viewer, deny permission
        # if self.object.restricted and not valid_viewer:
        if not valid_viewer:
            return PermissionDenied(self.request, 'You must be a member of the group ' + str(study.group))
        # Otherwise return the detail view
        return super(StudyViewerMixin, self).dispatch(*args, **kwargs)


# WIP (AND DEPRECATED)
class DetailRedirectMixin(object):
    """This mixin checks if the user has the object's group, if so it redirects to the edit page

    If the user does not have the correct group, it redirects to the details page

    Attributes:
    update_redirect_url - where to redirect it update is possible
    study - specifies what study to look to for permissions
    """
    # Default value for url to redirect to
    update_redirect_url = 'update/'
    # Default study as None
    study = None

    @method_decorator(login_required)
    @method_decorator(user_passes_test(user_is_active))
    def dispatch(self, *args, **kwargs):
        self.object = self.get_object()
        # If user CAN edit the item, redirect to the respective edit page
        # If the item is signed off on, it is no longer editable
        if is_group_editor(self.request.user, self.object.group.name) and not self.object.signed_off_by:
            # Redirects either to url + update or the specified url + object ID (as an attribute)
            # This is a little tricky if you don't look for {} in update_redirect_url
            return redirect(self.update_redirect_url.format(self.object.id))
        # If the object is restricted and the user is NOT a listed viewer
        elif self.study.access == 'editors' and not has_group(self.request.user, self.study.group.name):
            return PermissionDenied(
                self.request,
                'You do not have editor permissions for the group ' + str(self.study.group)
            )
        elif not self.study.access == 'public' and not is_group_viewer(self.request.user, self.study.group.name):
            return PermissionDenied(
                self.request,
                'You do not have viewer permissions for the group ' + str(self.study.group)
            )
        # Otherwise return the detail view
        return super(DetailRedirectMixin, self).dispatch(*args, **kwargs)


# NOT CURRENTLY USED
# Require user to be the creator or a group admin
class CreatorOrAdminRequiredMixin(object):
    """This mixin requires the user to be the creator of the object"""
    @method_decorator(login_required)
    @method_decorator(user_passes_test(user_is_active))
    # Deny access if not the CREATOR
    # Note the call for request.user.is_authenticated
    # Interestingly, Django wraps request.user until it is accessed
    # Thus, to perform this comparison it is necessary to access request.user via authentication
    def dispatch(self, *args, **kwargs):
        self.object = self.get_object()
        if not self.request.user.is_authenticated() or (self.request.user != self.object.created_by and not is_group_admin(self.request.user, self.object.group.name)):
            return PermissionDenied(self.request, 'You can only delete entries that you have created')
        return super(CreatorOrAdminRequiredMixin, self).dispatch(*args, **kwargs)


# Require user to be a group admin
class AdminRequiredMixin(object):
    """This mixin requires the user to be a group admin"""

    @method_decorator(login_required)
    @method_decorator(user_passes_test(user_is_active))
    def dispatch(self, *args, **kwargs):
        self.object = self.get_object()
        if not is_group_admin(self.request.user, self.object.group.name):
            return PermissionDenied(self.request, 'Only group admins can perform this action. Please contact your group admin.')
        return super(AdminRequiredMixin, self).dispatch(*args, **kwargs)


class DeletionMixin(object):
    """This mixin requires the user to be an admin and also needs the object to have no relations"""
    @method_decorator(login_required)
    @method_decorator(user_passes_test(user_is_active))
    def dispatch(self, *args, **kwargs):
        self.object = self.get_object()

        group = getattr(self.object, 'group', None)
        study = None
        study_sign_off = False

        if not group:
            study = getattr(self.object, 'study', None)
            group = study.group
            study_sign_off = study.signed_off_by

        group = group.name

        if not is_group_admin(self.request.user, group):
            return PermissionDenied(self.request, 'Only group admins can perform this action. Please contact your group admin.')

        if study_sign_off:
            return PermissionDenied(
                self.request,
                'You cannot modify this because the study has been signed off on by {0} {1}.'
                ' If something needs to be changed, contact the individual who signed off.'
                ' If you are the individual who signed off, please contact a database administrator.'.format(
                    study.signed_off_by.first_name,
                    study.signed_off_by.last_name
                )
            )

        can_be_deleted = True

        for current_field in self.object._meta.get_fields():
            # TODO MODIFY TO CHECK M2M MANAGERS IN THE FUTURE
            # TODO REVISE
            if str(type(current_field)) == "<class 'django.db.models.fields.reverse_related.ManyToOneRel'>":
                manager = getattr(self.object, current_field.name + '_set')
                count = manager.count()
                if count > 0:
                    can_be_deleted = False
                    break

        if not can_be_deleted:
            return PermissionDenied(
                self.request,
                'Other entries depend on this, so it cannot be deleted.'
                ' Either delete the linked entries or contact a Database Administrator if you would like to delete it.'
            )

        return super(DeletionMixin, self).dispatch(*args, **kwargs)


# Require the specified group or fail
class SpecificGroupRequiredMixin(object):
    """This mixin requires the user to have a specific group

    PLEASE NOTE: you must add the attribute 'required_group_name' to the view in question
    """
    @method_decorator(login_required)
    @method_decorator(user_passes_test(user_is_active))
    def dispatch(self, *args, **kwargs):
        if has_group(self.request.user, self.required_group_name):
            return super(SpecificGroupRequiredMixin, self).dispatch(*args, **kwargs)
        else:
            return PermissionDenied(
                self.request,
                'Contact an administrator if you would like to gain permission'
            )


class SuperuserRequiredMixin(object):
    """This mixin checks if the user has the group neccessary to at least view the entry"""
    @method_decorator(login_required)
    @method_decorator(user_passes_test(user_is_active))
    def dispatch(self, *args, **kwargs):
        if not self.request.user.is_authenticated() or not self.request.user.is_superuser:
            return PermissionDenied(self.request, 'You do not have permission to view this page.')
        return super(SuperuserRequiredMixin, self).dispatch(*args, **kwargs)
