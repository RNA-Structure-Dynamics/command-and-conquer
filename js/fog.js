$(document).ready(function () {
	var loader={
		loaded:true,
		loadedCount:0,
		load_image:function(imgUrl,callbackFunction){
			this.loaded = false;
			var image = new Image();
			image.src = 'images/'+imgUrl;
			$(image).bind('load',function() {
				this.loadedCount++;
				this.loaded=true;
				if (callbackFunction){
					callbackFunction();
				}
			});
			return image;
		}
	}
	var game={
	set_img:function(){
		this.img=loader.load_image('/maps/gdi/map01.jpeg',this.drawmap);
    },
	offsetX:0, // X & Y panning offsets for the map
	offsetY:0,
	animationTimeout:100,
	viewportWidth:0,
	viewportHeight:0,
	gridsize:24,
	panningThreshold:60, // Distance from edge of canvas at which panning starts
	panningSpeed:10,
	refreshBackground:true,
	running:true,
	items:[],
    drawmap:function(){
		game.ctx.drawImage(game.img,
    			0,0,game.viewportWidth,game.viewportHeight, 
    			0,0,game.viewportWidth,game.viewportHeight);
	},
	handlePanning:function(){
		if(!mouse.insideCanvas)return
		 if(mouse.x<=game.panningThreshold){
		if (game.offsetX>=game.panningSpeed){
		 game.refreshBackground = true;
		 game.offsetX -= game.panningSpeed;
		 }
		 } else if (mouse.x>= game.viewportWidth - game.panningThreshold){
		 if (game.offsetX + game.viewportWidth+ game.panningSpeed <= game.img.width){
		 game.refreshBackground = true;
		 game.offsetX += game.panningSpeed;
		 }
		 }

		 if(mouse.y<=game.panningThreshold){
		 if (game.offsetY>=game.panningSpeed){
		 game.refreshBackground = true;
		 game.offsetY -= game.panningSpeed;
		 }
		 } else if (mouse.y>= game.viewportHeight - game.panningThreshold){
		 if (game.offsetY + game.viewportHeight + game.panningSpeed <= game.img.height){
		 game.refreshBackground = true;
		 game.offsetY += game.panningSpeed;
		 }
	}
    },
	drawingLoop:function(){
		game.handlePanning();
		if (game.refreshBackground){
			game.ctx.drawImage(game.img,game.offsetX,game.offsetY,
			game.viewportWidth,game.viewportHeight, 0,0,game.viewportWidth,game.viewportHeight);
			game.refreshBackground = false;
		}
		game.foreground_ctx.clearRect(0,0,game.viewportWidth,game.viewportHeight);
		for(var i=0;i<game.items.length;i++)
				game.items[i].draw();
		mouse.draw_selected_rect()
	// Call the drawing loop for the next frame using request animation frame
		if (game.running){
			requestAnimationFrame(game.drawingLoop);
		}
	},
	animationLoop:function(){
		for(var i=0;i<game.items.length;i++)
				game.items[i].animate();
	},
	init:function(){
		game.canvas=$("#canvas")[0];
		game.ctx = game.canvas.getContext("2d");  
		game.foreground_canvas=$("#foreground_canvas")[0];
		game.foreground_ctx=game.foreground_canvas.getContext("2d");
		game.viewportWidth=game.canvas.width;
		game.viewportHeight=game.canvas.height;
		buildings.load('construction-yard');
		game.items.push(buildings.add({"type":"buildings","name":"construction-yard","x":11,"y":14}));
		game.items.push(buildings.add({"type":"buildings","name":"construction-yard","x":20,"y":14,"life":50}));
		}
	
	}
	
	var mouse={
		x:0,
		y:0,
		insideCanvas:false,
		dragSelect:false,
		buttonPressed:false,
		draw_selected_rect:function(){
			 if(this.dragSelect){
			 var x = Math.min(this.x,this.dragX);
			 var y = Math.min(this.y,this.dragY);
			 var width = Math.abs(this.x-this.dragX)
			 var height = Math.abs(this.y-this.dragY)
			 game.foreground_ctx.strokeStyle = 'white';
			 game.foreground_ctx.strokeRect(x,y, width, height);
			 }
		},
		init:function(){
			var $foreground_canvas=$("#foreground_canvas");
			$foreground_canvas.mousemove(function(ev){
				var offset = $foreground_canvas.offset();
				mouse.x = ev.pageX - offset.left;
				mouse.y = ev.pageY - offset.top;
				//console.log(mouse.x,mouse.y);
				if (mouse.buttonPressed){
					if ((Math.abs(mouse.dragX - mouse.x) > 4 || Math.abs(mouse.dragY - mouse.y)
						> 4)){
						mouse.dragSelect = true
					}
				} else {
				mouse.dragSelect = false;
				}
			});
			$foreground_canvas.mouseleave(function(ev) {
				mouse.insideCanvas = false;
			});
			$foreground_canvas.mouseenter(function(ev) {
				mouse.insideCanvas = true;
			});
			$foreground_canvas.mousedown(function(ev) {
				if(ev.which == 1){
					mouse.buttonPressed = true;
					mouse.dragX = mouse.x;
					mouse.dragY=mouse.y;
					//console.log("mousedown");
					ev.preventDefault();
				}
				return false;
			});
			$foreground_canvas.mouseup(function(ev) {
				if(ev.which == 1){
					mouse.buttonPressed = false;
					mouse.dragSelect=false;
					}
				return false;
			});
		}
		
	}

	var buildings={
		building_details:{
			'construction-yard':{
				imagesToLoad:[
        	        {name:'build',count:32},
        	        {name:"damaged",count:4},
        	        {name:'damaged-construct',count:20},
        	        {name:"healthy",count:4},
        	        {name:'healthy-construct',count:20},
        	        {name:"ultra-damaged",count:1}],
				pixelWidth:game.gridsize*3,
				pixelHeight:game.gridsize*2,
				hitPoints:400
			}
		},
		defaults:{
		type:"buildings",
		action:"construct",
		animationIndex:0,
		draw:function(){
			var x = (this.x*game.gridsize)-game.offsetX;
			var y = (this.y*game.gridsize)-game.offsetY;
			game.foreground_ctx.drawImage(this.spriteSheet,
			this.imageOffset*this.pixelWidth,0, this.pixelWidth, this.pixelHeight,
			x,y,this.pixelWidth,this.pixelHeight);	
		},
		animate:function(){
			if (this.life>this.hitPoints*0.4){
				 this.lifeCode = "healthy";
			} else if (this.life <= 0){
				 this.lifeCode = "ultra-damaged";
				 //game.remove(this);
				 //return;
			} else {
				 this.lifeCode = "damaged";
			}
			switch (this.action){
				 case "stand":
				 this.imageList = this.spriteArray[this.lifeCode];
				 this.imageOffset = this.imageList.offset + this.animationIndex;
				 this.animationIndex++;
				 if (this.animationIndex>=this.imageList.count){
				 this.animationIndex = 0;
				 }
				 break;
				 case "construct":
				 this.imageList = this.spriteArray["build"];
				 this.imageOffset = this.imageList.offset + this.animationIndex;
				 this.animationIndex++;
				 // Once constructing is complete go back to standing
				 if (this.animationIndex>=this.imageList.count){
				 this.animationIndex = 0;
				 this.action = "stand";
				 }
				 break;
				 }
		}
		},
		load:function(name){
			var item = this.building_details[name];
			item.spriteSheet = loader.load_image(this.defaults.type+'/'+name+'-sprite-sheet.png');
			item.spriteArray = [];
			item.spriteCount=0;
			for(var i=0;i<item.imagesToLoad.length;i++){
				var constructImageCount = item.imagesToLoad[i].count;
				var constructImageName = item.imagesToLoad[i].name;
					item.spriteArray[constructImageName] = {
					name:constructImageName,
					count:constructImageCount,
					offset:item.spriteCount
				};
				item.spriteCount+=constructImageCount;
			}
		},
		add:function(details){
			 var item = {};
			 var name = details.name;
			 $.extend(item,this.defaults);
			 $.extend(item,this.building_details[name]);
			 item.life=item.hitPoints;
			 $.extend(item,details);
			 return item;
		}
	}
	
	game.init();

	game.set_img();
	mouse.init();
	game.drawingLoop();
	game.animationLoop();
	game.animationInterval = setInterval(game.animationLoop,game.animationTimeout);
});


