console.log('loading screaan_exports ..');

/********************************************************************/
/**** script: 		screen_exports
/**** description: 	This script provides the functionaly to export 
                        'waterdieptekaart'
/********************************************************************/
var iframe_content = "<iframe height=25 scrolling='no' name='uploadFrame' width='150'" +
    "align='top' marginheight='0' marginwidth='0' frameborder='0' allowtransparency='true'></iframe>";
isc.Canvas.create({
    ID:'breadcrumbs',
    height:"15",
    contents: ror_config.breadcrumbs,
    autodraw:false
});

isc.ValuesManager.create({
        ID: "vm"        
});

isc.DataSource.create({
    ID: "dsTypeKering",
    showPrompt: false,
    dataFormat: "json",
    dataURL: locationFloodingData,
    transformRequest: function (dsRequest) {
	if (dsRequest.operationType == "fetch") {
	    var params = {action : 'get_ror_keringen_types'};
	    // combine paging parameters with criteria
	    return isc.addProperties({}, dsRequest.data, params);
	}
    },
    autoFetchData:true,
    fields:[
    	{name:"type", hidden: false, type:"text"}
    ]
});

isc.DataSource.create({
    ID: "dsRORKeringen",
    showPrompt: false,
    dataFormat: "json",
    dataURL: locationFloodingData,
    transformRequest: function (dsRequest) {
	if (dsRequest.operationType == "fetch") {
	    var params = {action : 'get_ror_keringen'};
	    // combine paging parameters with criteria
	    return isc.addProperties({}, dsRequest.data, params);
	}
    },
    autoDraw:false,
    fields:[
	{name: "id", primaryKey: true, hidden: true, type: "int"},
	{name: "title", hidden: false, type: "text", required: true},
	{name: "uploaded_at", hidden: true, type: "text"},
	{name: "owner", hidden: false, type: "text"},
	{name: "file_name", hidden: true, type: "text"},
	{name: "status", hidden: true, type:"text"},
	{name: "type_kering", hidden: true, type:"text"},
	{name: "type", hidden: true, type:"text", required: true},
	{name: "zip", hidden: true, type:"text", required: true},
	{name: "action", hidden: true, type:"text", required: true},
	{name: "description", hidden: false, type:"text", required: false}
    ]
});
    
isc.ListGrid.create({
    ID: "listGridKering",
    height:"100%",
    alternateRecordStyles:true,
    dataSource: dsRORKeringen,
    selectionType: "simple",
    autoFetchData: true,
    fields:[
	{name: "id", title:"ID", type:"int", width: 30},
	{name: "title", title: "Titel", type: "text", width: 150},
	{name: "uploaded_at", title: "Geüpload op", type: "text",width: 120},
	{name:"owner", title: "Eigenaar", type:"text", width: 150},
	{name:"file_name", title: "Bestandnaam", type:"text", width: 200},
	{name:"status", title: "Status", type:"text", width: 100},
	{name:"type_kering", title: "Type", type:"text", width: 100},
	{name:"description", title: "Opmerking", type:"text"}
    ],
    emptyMessage:"<br><br>Geen shape is beschikbaar."
});

isc.IButton.create({
    ID: "btUpload",
    title: "Upload",
    autoFit: true,
    icon: ror_config.root_url + "static_media/Isomorphic_NenS_skin/images/actions/upload.png",
    radioGroup: "views",
    actionType: "checkbox",
    click : function () {
	uploadWindow.show(); 
	uploadFrame.hide();
	uploadForm.reset()
    } 
});

isc.IButton.create({
    ID: "btSubmit",
    title: "Submit",
    autoFit: true,
    click : function () {
	var val = uploadForm.validate();
	if (val) {
	    uploadForm.submit();
	    uploadFrame.contents = iframe_content;
	    uploadFrame.redraw();
	    uploadFrame.show();
	} else {
	    console.log("Error on submit.");
    	}
    }
});

isc.IButton.create({
    ID: "btClose",
    title: "Close",
    autoFit: true,
    click : function () { 
	uploadWindow.hide();
	dsRORKeringen.fetchData({}, function(response, data, request){
	    listGridKering.setData(data);
	});
    }
});

isc.DynamicForm.create({
    ID: "uploadForm",
    dataSource: dsRORKeringen,
    action: locationFloodingData,
    target: "uploadFrame",
    dataFormat: "multipart/form-data",
    method: "POST",
    autoDraw: false,
    fields: [
	{ name: "title", required: true },
	{ name: "opmerking", required: false, type: "textArea" },
	{ name: "type", required: true, editorType: "select",
	  optionDataSource: "dsTypeKering" },
	{ name: "zip", type: "upload", required: true  },
	{ name: "action", type: "hidden", defaultValue: "upload_ror_keringen" }
    ],
    canSubmit: true
});

isc.Canvas.create({
    ID:'uploadFrame',
    height: 25,
    contents: iframe_content,
    autodraw: false,
    autoFit: true
});

isc.HLayout.create({
    ID: "uploadWindowButtons",
    membersMargin: 5,
    padding: 5,
    height: 20,
    members: [btSubmit, btClose, uploadFrame]
});

isc.Window.create({
    ID: "uploadWindow",
    title: "Upload kering",
    autoSize:true,
    autoCenter: true,
    isModal: true,
    showModalMask: true,
    autoDraw: false,
    closeClick : function () { 
	dsRORKeringen.fetchData({}, function(response, data, request){
	    listGridKering.setData(data);
	});
	this.Super("closeClick", arguments)
    },
    items: [
	uploadForm,	
	uploadWindowButtons
    ]
});

isc.HLayout.create({
    ID: "buttons",
    width: 500,
    membersMargin: 5,
    padding: 5,
    members: [btUpload]
});

isc.VLayout.create({
    ID: "mainLayout",
    width: "100%",
    height: "100%",
    membersMargin: 10,
    members: [breadcrumbs, buttons, listGridKering]
});

var downloadButtons = function() {
    var dButtons = new Array();
    for (var i=0; i < ror_files.length; i++) {
	var fileName = ror_files[i].name;
	var path = ror_files[i].path;
	console.log(i + " " + fileName);
 	dButtons[i] = isc.IButton.create({
	    ID: fileName.split(".")[0] + i,
	    title: "Download " + fileName.split(".")[0],
	    path: path,
	    autoFit: true,
	    icon: isomorphicDir + "skins/SmartClient/images/actions/download.png",
	    radioGroup: "views",
	    actionType: "checkbox",
	    click: 'console.log("PATH: " + this.path); window.open(this.path, "uploadFrame");'
	});
    }
    return dButtons;
}

buttons.addMembers(downloadButtons());