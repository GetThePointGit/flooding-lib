#alphabetical order
from lizard.flooding.models import Attachment, Breach, BreachSobekModel, CutoffLocation, CutoffLocationSet,        \
                    CutoffLocationSobekModelSetting, Dike, ExternalWater,\
                    PermissionProjectGridDataLegend, PermissionProjectShapeDataLegend, \
                    Project, ProjectGroupPermission, Region, RegionSet, Result, ResultType,         \
                    ResultType_PresentationType, Scenario, ScenarioBreach, ScenarioCutoffLocation,  \
                    Scenario_PresentationLayer,  SobekModel, SobekVersion, Task, TaskType,          \
                    UserPermission, Waterlevel, WaterlevelSet, ExternalWater, ExtraInfoField, ExtraScenarioInfo
    
from lizard.presentation.models import PresentationLayer, PresentationType

from django.contrib import admin
from django.contrib import databrowse
from django.contrib.gis.admin import OSMGeoAdmin


class ProjectGroupPermissionInline(admin.TabularInline):   
    model = ProjectGroupPermission
    extra = 8

class RegionAdmin(OSMGeoAdmin):
    list_filter = ('active', 'sobekmodels', )
    search_fields = ['name', 'longname', ]

class ProjectGroupPermissionAdmin(admin.ModelAdmin):
    list_filter = ('group', 'project', 'permission',)

class TaskAdmin(admin.ModelAdmin):
    list_display = ['scenario', 'tasktype', 'tstart', 'tfinished', 'successful',]
    list_filter = ('tstart', 'tasktype', 'successful', 'scenario', )

class ScenarioBreachAdmin(admin.ModelAdmin):
    list_filter = ('sobekmodel_externalwater', 'methstartbreach', )

class ScenarioAdmin(admin.ModelAdmin):
    #'breaches','breaches_region',
    list_display = [ '__unicode__', 'get_status_str', ]
    list_filter = ('calcpriority', 'owner', 'project', )
    #inlines = [PresentationLayerInline]
    
class ResultTypeAdmin(admin.ModelAdmin):
    list_display = ['name', ]
    #inlines = [PresentationTypeInline]    

class CutoffLocationAdmin(admin.ModelAdmin):
    list_display = ['__unicode__', 'isinternal', ]
    

class Scenario_PresentationLayerAdmin(admin.ModelAdmin):
    list_display = [ 'scenario','presentationlayer', ]
    
class ResultType_PresentationTypeAdmin(admin.ModelAdmin):
    list_display = ['remarks', 'resulttype', 'presentationtype', ]   

class WaterlevelAdmin(admin.ModelAdmin):
    list_filter = ('waterlevelset', )

class ProjectAdmin(admin.ModelAdmin):
    #list_filter = ('waterlevelset', )    
    inlines = [ProjectGroupPermissionInline]

#alphabetical order
admin.site.register(Attachment)
admin.site.register(Breach)
admin.site.register(BreachSobekModel)
admin.site.register(CutoffLocationSobekModelSetting)
admin.site.register(CutoffLocation, CutoffLocationAdmin)
admin.site.register(CutoffLocationSet)
admin.site.register(Dike)
admin.site.register(ExternalWater)
admin.site.register(ExtraInfoField)
admin.site.register(ExtraScenarioInfo)
admin.site.register(PermissionProjectShapeDataLegend)
admin.site.register(PermissionProjectGridDataLegend)
admin.site.register(Project, ProjectAdmin)
admin.site.register(ProjectGroupPermission, ProjectGroupPermissionAdmin)
admin.site.register(Region, RegionAdmin)
admin.site.register(RegionSet)
admin.site.register(Result)
admin.site.register(ResultType, ResultTypeAdmin)
admin.site.register(ResultType_PresentationType, ResultType_PresentationTypeAdmin)   # 
admin.site.register(Scenario, ScenarioAdmin)
admin.site.register(ScenarioBreach, ScenarioBreachAdmin)
admin.site.register(ScenarioCutoffLocation)
admin.site.register(Scenario_PresentationLayer, Scenario_PresentationLayerAdmin)   
admin.site.register(SobekModel)
admin.site.register(SobekVersion)
admin.site.register(Task, TaskAdmin)
admin.site.register(TaskType)
admin.site.register(UserPermission)
admin.site.register(Waterlevel, WaterlevelAdmin)
admin.site.register(WaterlevelSet)
