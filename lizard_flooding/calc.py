import logging

import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.ticker import FormatStrFormatter, LinearLocator

from lizard_flooding.models import WaterlevelSet, ExternalWater
from lizard_presentation.views import get_time_step_locators, TimestepFormatter

log = logging.getLogger('nens.web.flooding.calc')


def get_interval_seconds(string):
    return 50000


class BoundaryConditions:

    def __init__(self, breach, extwmaxlevel, tpeak, tstorm, tsim, tstartbreach = 0, tdeltaphase = 0, tide_id = None, extwbaselevel = None):
        self.timePeakStorm = 0
        self.breach = breach
        self.extwmaxlevel = extwmaxlevel
        self.tpeak = tpeak
        self.tstorm = tstorm
        self.tsim = tsim
        self.tstartbreach = tstartbreach
        self.tdeltaphase = tdeltaphase
        self.tide_id = tide_id
        self.extwbaselevel = extwbaselevel
        
        self.useManualWaterlevels = False
        self.manualWaterlevels = []

    def get_max_storm_tide(self, tidewaterlevels):
        maxtide = tidewaterlevels.order_by('-value')[0]
        stormpeak = None
        min_storm_level = 10000
        for tide in tidewaterlevels:
             stormfactor = self.stormvalue(tide.time - maxtide.time + self.tdeltaphase, 1)
             if stormfactor > 0:
                 stormvalue_if_peak_is_at_this_moment = (self.extwmaxlevel - tide.value) / stormfactor

                 if stormvalue_if_peak_is_at_this_moment < min_storm_level:
                     #print 'new peak: ' + str(tide)
                     stormpeak = tide
                     min_storm_level = stormvalue_if_peak_is_at_this_moment
        return (maxtide, stormpeak, min_storm_level)

    def stormvalue(self, timestamp, max_stormlevel):
        rel2storm = timestamp - self.timePeakStorm
        if abs(rel2storm) < 0.5 * self.tpeak:
            return max_stormlevel
        elif abs(rel2storm) < 0.5 * self.tstorm:
            return (1 - (abs(rel2storm) - (0.5 * self.tpeak)) / (0.5 * self.tstorm - 0.5 * self.tpeak)) * max_stormlevel
        else:
            return 0

    def get_waterlevels(self, tstart = -1000, tend = 1000):
        if self.useManualWaterlevels:
            return self.manualWaterlevels
        else:
            waterleveltbl = []
            if self.breach.externalwater.type == ExternalWater.TYPE_SEA:
                tide = WaterlevelSet.objects.get(pk = self.tide_id)
                tidewaterlevels = tide.waterlevel_set.order_by('time')
    
                #get max of tide
                maxtide, max_storm_tide, maxlevel_storm = self.get_max_storm_tide(tidewaterlevels)
    
                #relative to tide timestamps
                beginsimulation_rel = max_storm_tide.time + self.tstartbreach
                tidewaterlevels = tidewaterlevels.filter(time__gt = tstart + beginsimulation_rel ).exclude(time__gt = tend + beginsimulation_rel )
    
                for tide in tidewaterlevels:
                    time_rel = tide.time - beginsimulation_rel
                    stormlevel = self.stormvalue(tide.time - maxtide.time + self.tdeltaphase, maxlevel_storm )
                    waterlevel = stormlevel + tide.value
                    waterleveltbl.append({'time':time_rel,'stormlevel':stormlevel, 'waterlevel':waterlevel })
    
            elif self.breach.externalwater.type == ExternalWater.TYPE_LAKE:
                waterleveltbl.append({'time':-0.5*self.tstorm, 'waterlevel':self.extwbaselevel })
                waterleveltbl.append({'time':-0.5*self.tpeak, 'waterlevel':self.extwmaxlevel })
                waterleveltbl.append({'time':0.5*self.tpeak, 'waterlevel':self.extwmaxlevel })
                waterleveltbl.append({'time':0.5*self.tstorm, 'waterlevel':self.extwbaselevel })
                if self.tsim > 0.5*self.tpeak:
                    waterleveltbl.append({'time':self.tsim, 'waterlevel':self.extwbaselevel })
    
            else:
                waterleveltbl.append({'time':0, 'waterlevel':self.extwmaxlevel })
                waterleveltbl.append({'time':self.tsim, 'waterlevel':self.extwmaxlevel })

            return waterleveltbl
    
    def set_waterlevels(self, waterlevel_string):
        self.waterleveltbl = []
        self.useManualWaterlevels = True
        
        for line in waterlevel_string.split('|'):
            lineparts = line.split(',');  
            self.waterleveltbl.append({'time':get_interval_seconds(lineparts[0]), 'waterlevel':lineparts[1]})

    def get_graph(self, destination, width, height):

        """
            - This service returns a PNG image with the given width and height
            - The PNG contains a graph of the results belonging to the result_id and sobek_ids
        input:
            widht and height of returning image
            array of shape_ids which will be shown
            presentationlayer_id

        return:
            png
        """
        # Opmerking Bastiaan: caching van his-object geeft weinig tijdwinst


        #Get information from request
        graph_width = width
        graph_height = height

        #Set dpi
        graph_dpi = 55

        #Create figure and subplot to draw on
        fig = plt.figure(facecolor='white', edgecolor='white', figsize=(graph_width/graph_dpi, graph_height/graph_dpi), dpi=graph_dpi)

        #Add axes 'manually' (not via add_subplot(111) to have control over the position
        #This is necessary as we use long labels
        ax_left = 0.11
        ax_bottom  = 0.21
        ax=fig.add_axes([ax_left, ax_bottom, 0.95-ax_left, 0.95-ax_bottom])

        #Read Sobek data and plot it
        plots=dict() # dictionary necessary for creating the legend at the end of this method

        # get values
        table = self.get_waterlevels( -0.25*self.tsim, 1.25*self.tsim )


        time_steps  = [obj['time']*24 for obj in table]
        if table[0].has_key('stormlevel'):
            use_stormlevel = True
            stormlevel = [obj['stormlevel'] for obj in table]
        else:
            use_stormlevel = False
            stormlevel = [0,]
        waterlevel = [obj['waterlevel'] for obj in table]

        min_level = min(min(stormlevel),min(waterlevel))
        max_level = max(max(stormlevel),max(waterlevel))

        simperiod_levels = [min_level, max_level, max_level , min_level]
        simperiod_times = [0, 0, self.tsim*24, self.tsim*24]

        plot_simperiod = ax.plot(simperiod_times, simperiod_levels, '-', linewidth = 3)
        if use_stormlevel:
            plot_stormlevel =  ax.plot(time_steps, stormlevel, '-', linewidth = 3)
        plot_waterlevel =  ax.plot(time_steps, waterlevel, '-', linewidth = 3)

        plots['waterlevel'] = plot_waterlevel
        if use_stormlevel:
            plots['stormlevel'] = plot_stormlevel
        plots['simulatie periode'] = plot_simperiod

        #temp fix for locators
        dt = time_steps[-1]- time_steps[0]/len(time_steps)
        if dt > 50:
            dt = 10
        else:
            dt = 1

        [min_locator, maj_locator] = get_time_step_locators(len(time_steps), dt)

        #Set formatting of the x-axis and y-axis
        ax.xaxis.set_major_formatter(TimestepFormatter())
        ax.xaxis.set_major_locator(maj_locator)
        ax.xaxis.set_minor_locator(min_locator)
        fig.autofmt_xdate()

        ax.yaxis.set_major_locator(LinearLocator())
        ax.yaxis.set_major_formatter(FormatStrFormatter('%0.2f'))

        ax.grid(True, which='major')
        ax.grid(True, which='minor')

        #Set labels
        plt.xlabel("Tijdstip")
        plt.ylabel("waterstand [mNAP]")
        ax.set_title("waterstandsverloop")

        #Set legend
        ax.legend((v for k,v in plots.iteritems()), (k for k,v in plots.iteritems()), 'upper right', shadow=True)

        #Return figure as png-file
        log.debug(  'start making picture' )
        canvas = FigureCanvas(fig)
        canvas.print_png(destination)
        log.debug( 'ready making picture' )
        return destination



