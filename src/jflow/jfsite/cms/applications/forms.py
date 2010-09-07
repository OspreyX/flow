from django import forms
from django.contrib.auth.models import User

from djpcms.utils import form_kwargs
from djpcms.utils.html import htmlwrap, box, ModelMultipleChoiceField, AutocompleteManyToManyInput
from djpcms.utils.uniforms import FormLayout, Html, Fieldset, inlineLabels, ModelFormInlineHelper

from flowrepo.models import Report, Attachment, Image
from flowrepo.forms import FlowItemForm, add_related_upload
from flowrepo import markups

from tagging.models import Tag
from tagging.forms import TagField

from jflow.db.instdata.models import DataId, EconometricAnalysis, VendorId
from jflow.db.instdata.forms import DataIdForm, EconometricForm


CRL_HELP = htmlwrap('div',
                    htmlwrap('div',markups.help()).addClass('body').render()
                   ).addClasses('flowitem report').render()


collapse = lambda title, html, c, cl: box(hd = title, bd = html, collapsable = c, collapsed = cl)


def AutocompleteTagField(required = False):
    wg = AutocompleteManyToManyInput(Tag, ['name'], separator = ' ', inline = True)
    return TagField(required = required, widget = wg)


class NiceDataIdForm(DataIdForm):
    tags   = AutocompleteTagField()
    
    layout = FormLayout()
    #layout = FormLayout(
    #                     Fieldset('code', 'name', 'isin', 'firm_code', 'content_type',
    #                              'tags', 'country',
    #                              css_class = inlineLabels, key = 'main'),
    #                     Fieldset('description', key = 'descr'),
    #                     Fieldset('live', 'default_vendor',
    #                              css_class = inlineLabels, key = 'second'),
    #                     template = 'instdata/dataid_change_form.html')
    layout.inlines.append(ModelFormInlineHelper(DataId,VendorId))


class InstrumentForm(forms.ModelForm):
    pass


class ReportForm(FlowItemForm):
    authors  = ModelMultipleChoiceField(User.objects, required = False)
    data_ids = ModelMultipleChoiceField(DataId.objects, required = False, label = 'Related securities')
    attachments  = ModelMultipleChoiceField(Attachment.objects,
                                            required = False,
                                            label = 'Available attachments',
                                            help_text = 'To select/deselect multiple files to attach press ctrl')
    images       = ModelMultipleChoiceField(Image.objects, required = False, label = 'Available images',
                                            help_text = 'To select/deselect multiple files to attach press ctrl')
    tags         = AutocompleteTagField()
    attachment_1 = forms.FileField(required = False)
    attachment_2 = forms.FileField(required = False)
    attachment_3 = forms.FileField(required = False)
    
    layout = FormLayout(
                             Fieldset('name', 'description', 'body', key = 'body'),
                    
                             Fieldset('visibility', 'allow_comments',
                                      css_class = inlineLabels),
                            
                             Fieldset('authors', 'tags', 'data_ids'),
                             
                             Html(CRL_HELP, key = 'help',
                                      renderer = lambda html : collapse('Writing Tips',html,True,True)),
                            
                             Fieldset('attachments', 'images',
                                      key = 'current_attachments',
                                      renderer = lambda html : collapse('Attached files',html,True,False)),
                             
                             Fieldset('attachment_1', 'attachment_2', 'attachment_3',
                                      key = 'attachments',
                                      renderer = lambda html : collapse('New attachments',html,True,False)),
                                      
                             Fieldset('slug', 'timestamp', 'markup', 'parent',
                                      key = 'metadata',
                                      renderer = lambda html : collapse('Metadata',html,True,True)),
                    
                             template = 'flowrepo/report_form.html')
    
    def save(self, commit = True):
        instance = super(ReportForm,self).save(commit = commit)
        add_related_upload(self.cleaned_data['attachment_1'],instance)
        add_related_upload(self.cleaned_data['attachment_2'],instance)
        add_related_upload(self.cleaned_data['attachment_3'],instance)
        return instance
    
    class Meta:
        model = Report