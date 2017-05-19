from __future__ import absolute_import

from django import forms
from django.http import HttpResponse
from django.views.generic import View
from django.utils.decorators import method_decorator

# from social_auth.models import UserSocialAuth

from sentry.web.decorators import login_required
from sentry.web.helpers import render_to_response

from sentry_plugins.github.models import GitHubInstallation
# from .client import GitHubClient


class OrganizationForm(forms.Form):
    organization = forms.ChoiceField()

    def __init__(self, organizations, *args, **kwargs):
        super(OrganizationForm, self).__init__(*args, **kwargs)
        self.fields['organization'].choices = organizations


class GitHubInstallationSetupView(View):

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(GitHubInstallationSetupView, self).dispatch(request, *args, **kwargs)

    def handle(self, request):
        try:
            installation_id = int(request.GET['installation_id'])
        except (KeyError, ValueError):
            return HttpResponse(status=400)

        try:
            installation = GitHubInstallation.objects.get(
                installation_id=installation_id,
            )
        except GitHubInstallation.DoesNotExist:
            return HttpResponse(status=400)

        if request.method == 'GET':
            form = OrganizationForm(
                [(o.id, o.name) for o in request.user.get_orgs()],
                {'organization': installation.organization_id} if installation.organization_id else None,
            )
        else:
            form = OrganizationForm(
                [(o.id, o.name) for o in request.user.get_orgs()],
                request.POST,
            )
            if form.is_valid():
                # TODO(jess): this isn't actually working, but
                # we need to somehow verify user has access
                # to this installation

                # auth = UserSocialAuth.objects.filter(
                #     user=request.user,
                #     provider='github',
                # ).first()
                # client = GitHubClient(token=auth.tokens['access_token'])
                # installations = client.get_installations()
                installation.organization_id = int(form.cleaned_data['organization'])
                installation.save()

        return render_to_response('setup.html', {'form': form}, request)

    def get(self, request):
        return self.handle(request)

    def post(self, request):
        return self.handle(request)
