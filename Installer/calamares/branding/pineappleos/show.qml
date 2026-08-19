import QtQuick 2.15
import QtQuick.Controls 2.15

// ============================================================================
//  Apresentacao visual propria do instalador Pineapple OS
// ============================================================================
SlideShow {
    property bool loop: true
    property int timeOut: 3000

    Image {
        id: slideImage
        source: "slide1.svg"
        anchors.fill: parent
        fillMode: Image.PreserveAspectFit
        opacity: 0.94
    }

    Timer {
        interval: timeOut
        running: true
        repeat: true
        onTriggered: {
            if (slideImage.source.toString().indexOf("slide1") !== -1) {
                slideImage.source = "slide2.svg";
            } else if (slideImage.source.toString().indexOf("slide2") !== -1) {
                slideImage.source = "slide3.svg";
            } else {
                slideImage.source = "slide1.svg";
            }
        }
    }

    Text {
        id: caption
        color: "#163b32"
        anchors.bottom: parent.bottom
        anchors.horizontalCenter: parent.horizontalCenter
        font.pixelSize: 19
        font.bold: true
        text: qsTr("Pineapple OS - seu computador, do seu jeito.")
    }
}
