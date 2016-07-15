from django.views.generic import DetailView, CreateView, UpdateView
from django.shortcuts import redirect, render_to_response
from django.template import RequestContext
from django import forms
from django.forms.models import inlineformset_factory
from .forms import MicrodeviceForm, OrganModelForm, OrganModelProtocolInlineFormset
from .models import Microdevice, OrganModel, ValidatedAssay, OrganModelProtocol
from mps.mixins import SpecificGroupRequiredMixin

# class MicrodeviceList(ListView):
#     model = Microdevice
#     template_name = 'microdevices/microdevice_list.html'


# Convert to class?
def microdevice_list(request):
    """Displays a list of Devices AND Models"""
    c = RequestContext(request)

    organ_models = OrganModel.objects.prefetch_related('organ', 'center', 'device').all()
    devices = Microdevice.objects.prefetch_related('organ', 'center', 'manufacturer').all()

    c.update({
        'models': organ_models,
        'devices': devices,
    })

    return render_to_response('microdevices/microdevice_list.html', c)


class OrganModelDetail(DetailView):
    """Displays details for an Organ Model"""
    model = OrganModel
    template_name = 'microdevices/organmodel_detail.html'

    def get_context_data(self, **kwargs):
        context = super(OrganModelDetail, self).get_context_data(**kwargs)

        assays = ValidatedAssay.objects.filter(organ_model=self.object).prefetch_related('assay', 'assay__assay_type')

        if any(i in self.object.center.groups.all() for i in self.request.user.groups.all()):
            protocols = OrganModelProtocol.objects.filter(
                organ_model=self.object
            ).order_by('-version')
        else:
            protocols = None

        context.update({
            'assays': assays,
            'protocols': protocols,
        })

        return context


# def organ_model_detail(request, *args, **kwargs):
#     c = RequestContext(request)
#
#     model = get_object_or_404(OrganModel, pk=kwargs.get('pk'))
#     assays = ValidatedAssay.objects.filter(organ_model=model).prefetch_related('assay', 'assay__assay_type')
#     protocols = OrganModelProtocol.objects.filter(organ_model=model).order_by('-version')
#
#     c.update({
#         'model': model,
#         'assays': assays,
#         'protocols': protocols,
#     })
#
#     return render_to_response('microdevices/organmodel_detail.html', c)


class MicrodeviceDetail(DetailView):
    """Displays details for a Device"""
    model = Microdevice
    template_name = 'microdevices/microdevice_detail.html'


class MicrodeviceAdd(SpecificGroupRequiredMixin, CreateView):
    """Allows the addition of Devices"""
    model = Microdevice
    template_name = 'microdevices/microdevice_add.html'
    form_class = MicrodeviceForm

    required_group_name = 'Change Microdevices Front'

    def form_valid(self, form):
        if form.is_valid():
            self.object = form.save()
            self.object.modified_by = self.request.user
            self.object.save()
            return redirect('/microdevices/')
        else:
            return self.render_to_response(self.get_context_data(form=form))


class MicrodeviceUpdate(SpecificGroupRequiredMixin, UpdateView):
    """Allows Devices to be updated"""
    model = Microdevice
    template_name = 'microdevices/microdevice_add.html'
    form_class = MicrodeviceForm

    required_group_name = 'Change Microdevices Front'

    def get_context_data(self, **kwargs):
        context = super(MicrodeviceUpdate, self).get_context_data(**kwargs)
        context['update'] = True
        return context

    def form_valid(self, form):
        if form.is_valid():
            self.object = form.save()
            self.object.modified_by = self.request.user
            self.object.save()
            return redirect('/microdevices/')
        else:
            return self.render_to_response(self.get_context_data(form=form))

OrganModelProtocolFormset = inlineformset_factory(
    OrganModel,
    OrganModelProtocol,
    formset=OrganModelProtocolInlineFormset,
    extra=1,
    exclude=[],
    widgets={
        'version': forms.TextInput(attrs={'size': 10})
    }
)


class OrganModelAdd(SpecificGroupRequiredMixin, CreateView):
    """Allows the addition of Organ Models"""
    model = OrganModel
    template_name = 'microdevices/organmodel_add.html'
    form_class = OrganModelForm

    required_group_name = 'Change Microdevices Front'

    def get_context_data(self, **kwargs):
        context = super(OrganModelAdd, self).get_context_data(**kwargs)
        if 'formset' not in context:
            if self.request.POST:
                context['formset'] = OrganModelProtocolFormset(self.request.POST, self.request.FILES)
            else:
                context['formset'] = OrganModelProtocolFormset()

        return context

    def form_valid(self, form):
        formset = OrganModelProtocolFormset(
            self.request.POST,
            self.request.FILES,
            instance=form.instance
        )
        if form.is_valid() and formset.is_valid():
            self.object = form.save()
            self.object.modified_by = self.request.user
            self.object.save()
            formset.save()
            return redirect('/microdevices/')
        else:
            return self.render_to_response(self.get_context_data(form=form))


class OrganModelUpdate(SpecificGroupRequiredMixin, UpdateView):
    """Allows Organ Models to be updated"""
    model = OrganModel
    template_name = 'microdevices/organmodel_add.html'
    form_class = OrganModelForm

    required_group_name = 'Change Microdevices Front'

    def get_context_data(self, **kwargs):
        context = super(OrganModelUpdate, self).get_context_data(**kwargs)
        if 'formset' not in context:
            if self.request.POST:
                context['formset'] = OrganModelProtocolFormset(
                    self.request.POST,
                    self.request.FILES,
                    instance=self.object
                )
            else:
                context['formset'] = OrganModelProtocolFormset(instance=self.object)

        context['update'] = True

        return context

    def form_valid(self, form):
        formset = OrganModelProtocolFormset(
            self.request.POST,
            self.request.FILES,
            instance=form.instance
        )
        if form.is_valid() and formset.is_valid():
            self.object = form.save()
            self.object.modified_by = self.request.user
            self.object.save()
            formset.save()
            return redirect('/microdevices/')
        else:
            return self.render_to_response(self.get_context_data(form=form))
