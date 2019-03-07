/*
 *
 * Dual Input Pane Plugin (Requires splithandler plugin)
 *
 * This adds a second input window for games that really benefit from having two separate,
 * high-complexity commands being created at the same time.
 *
 * Note: Incompatible with hotbuttons plugin because both Split() the same location
 *       Split.js doesn't seem to support adding multiple splits at the same <tag> level.
 */
plugin_handler.add('dual_input', (function () {
    //
    //
    var splitHandlerUI = function ( input2 ) {
        input2.addClass( 'split split-vertical' );

        // Add second inputform between the existing #main and #inputform,
        // replacing the previous gutter div added by the splithandler plugin
        $('#input').prev().replaceWith(input2);

        Split(['#main','#input2','#input'], {
            sizes: [80,10,10],
            direction: 'vertical',
            gutterSize: 4,
            minSize: [150,50,50],
        });
    }


    //
    //
    var goldenLayoutUI = function ( input2 ) {
        var myLayout = plugins['goldenlayout'].getGL();
        var input = myLayout.root.getComponentsByName('input');

        myLayout.registerComponent( 'input2', function (container, componentState) {
            input2.addClass( 'content' );
            input2.appendTo( container.getElement() );
        });

        input.addChild({
            title: 'input2',
            type: 'component',
            componentName: 'input2',
            componentId: 'input',
        });
    }


    //
    // onKeydown check if the second inputfield is focused.
    // If so, send the input on '<Enter>' key.
    var onKeydown = function () {
        let inputfield = $("#inputfield2");
        if ( inputfield.is(":focus") ) {
            if( (event.which === 13) && (!event.shiftKey) ) {
                var outtext = inputfield.val();
                var lines = outtext.trim().replace(/[\r\n]+/,"\n").split("\n");

                for (var i = 0; i < lines.length; i++) {
                    plugin_handler.onSend( lines[i].trim() );
                }

                inputfield.val('');
                event.preventDefault();
                return true;
            }
        }
        return false;
    }

    //
    // Initialize me
    var init = function() {
        var input2 = $( [
              '<div id="input2">',
              ' <textarea id="inputfield2" type="text"></textarea>',
              '</div>',
            ].join("\n") );

        if( plugins.hasOwnProperty('splithandler') ) {
            splitHandlerUI(input2);
        }

        if( plugins.hasOwnProperty('goldenlayout') ) {
            goldenLayoutUI(input2);
        }

        $('#inputfield2').css({
            "display": "inline",
            "height": "100%",
            "width": "100%",
            "background-color": "black",
            "color": "white",
            "padding": "0 .45rem",
            "font-size": "1.1rem",
            "font-family": "'DejaVu Sans Mono', Consolas, Inconsolata, 'Lucida Console', monospace"
            });

        console.log("Dual Input Plugin Initialized.");
    }

    return {
        init: init,
        onKeydown: onKeydown,
    }
})());
