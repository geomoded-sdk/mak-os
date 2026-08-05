import QtQuick 2.15
import QtQuick.Controls 2.15

// ============================================================================
//  Apresentação de slides do instalador Calamares do Mak OS
// ============================================================================
SlideShow {
    property bool loop: true
    property int timeOut: 3000

    Image {
        id: slideImage
        source: "slide1.svg"
        anchors.fill: parent
        fillMode: Image.PreserveAspectFit
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
        color: "#f2f3f7"
        anchors.bottom: parent.bottom
        anchors.horizontalCenter: parent.horizontalCenter
        font.pixelSize: 22
        font.bold: true
        text: qsTr("Mak OS — rápido, bonito e livre.")
    }
}
