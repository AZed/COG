from django.forms import Form, ModelForm, CharField
from cog.models import *
from cog.utils import default_clean_field, clean_url_field

class BookmarkForm(ModelForm):
    
    class Meta:
        model = Bookmark
        exclude = ('type')
        
    # override __init__ method to provide a filtered list of options for the bookmark folder
    def __init__(self, project, *args,**kwargs):
        
        super(BookmarkForm, self ).__init__(*args,**kwargs)
        
        # filter parent posts by project and type
        self.fields['folder'].queryset = Folder.objects.filter(project=project).distinct().order_by('order')
        # remove the empty option
        self.fields['folder'].empty_label = None
        
    def clean_url(self):
        return clean_url_field(self, 'url')
    
    def clean_name(self):
        return default_clean_field(self, 'name')
    
    def clean_description(self):
        return default_clean_field(self, 'description')

class FolderForm(ModelForm):
    
    class Meta:
        model = Folder
        
    # override __init__ method to provide a filtered list of options for the bookmark folder
    def __init__(self, project, *args,**kwargs):
        
        super(FolderForm, self ).__init__(*args,**kwargs)
                
        # filter parent posts by project and type
        self.fields['parent'].queryset = Folder.objects.filter(project=project).exclude(id=self.instance.id).distinct().order_by('order')
        # exclude the option for no parent - all folders created after the first must have parent
        self.fields['parent'].empty_label = None
        
    def clean_name(self):
        return default_clean_field(self, 'name')