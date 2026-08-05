import QtQuick 2.0
import QtQuick.Controls 2.12
import SddmComponents 2.0

// =============================================================================
//  Mak OS — tema de login do SDDM
//  Identidade própria: grafite + gradiente azul-petróleo, marca "M" em coral.
// =============================================================================

Rectangle {
    id: root
    width: Screen.width
    height: Screen.height

    property string lastError: ""

    gradient: Gradient {
        GradientStop { position: 0.0; color: "#101820" }
        GradientStop { position: 1.0; color: "#1d2a38" }
    }

    // fundo sutil (gerado por Scripts/gen-backgrounds.py)
    Image {
        anchors.fill: parent
        source: "background.png"
        fillMode: Image.PreserveAspectCrop
        opacity: 0.35
    }

    // ---- identidade ----
    Column {
        id: brand
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        anchors.topMargin: Screen.height * 0.12
        spacing: 10

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "M"
            font.family: "Sans"
            font.bold: true
            font.pixelSize: Math.round(Screen.height * 0.08)
            color: "#4f9dde"
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Mak OS"
            font.pixelSize: Math.round(Screen.height * 0.026)
            font.bold: true
            color: "#f5f6f8"
        }

        Text {
            id: clockLabel
            anchors.horizontalCenter: parent.horizontalCenter
            text: clockTimer.text
            font.pixelSize: Math.round(Screen.height * 0.015)
            color: "#9aa5b1"
        }
    }

    Timer {
        id: clockTimer
        property string text: ""
        interval: 1000
        running: true
        repeat: true
        onTriggered: text = Qt.formatDateTime(new Date(), "dddd, d MMMM   HH:mm")
    }

    // ---- formulário de login ----
    Column {
        id: form
        anchors.centerIn: parent
        width: Math.max(Screen.width * 0.26, 340)
        spacing: 12

        Text {
            id: errorText
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            text: root.lastError
            color: "#e2776f"
            font.pixelSize: 14
            visible: root.lastError.length > 0
            wrapMode: Text.WordWrap
        }

        TextField {
            id: username
            width: parent.width
            height: 46
            placeholderText: "Usuário"
            color: "#f5f6f8"
            placeholderTextColor: "#7a8794"
            font.pixelSize: 16
            background: Rectangle {
                radius: 9
                color: Qt.rgba(1, 1, 1, 0.06)
                border.color: username.activeFocus ? "#4f9dde" : Qt.rgba(1, 1, 1, 0.15)
                border.width: username.activeFocus ? 2 : 1
            }
            onAccepted: password.forceActiveFocus()
        }

        TextField {
            id: password
            width: parent.width
            height: 46
            placeholderText: "Senha"
            echoMode: TextInput.Password
            color: "#f5f6f8"
            placeholderTextColor: "#7a8794"
            font.pixelSize: 16
            background: Rectangle {
                radius: 9
                color: Qt.rgba(1, 1, 1, 0.06)
                border.color: password.activeFocus ? "#4f9dde" : Qt.rgba(1, 1, 1, 0.15)
                border.width: password.activeFocus ? 2 : 1
            }
            onAccepted: doLogin()
            Keys.onEscapePressed: {
                username.text = ""
                password.text = ""
                root.lastError = ""
                username.forceActiveFocus()
            }
        }

        Button {
            id: loginButton
            width: parent.width
            height: 46
            text: "Entrar"
            contentItem: Text {
                text: parent.text
                color: "#101418"
                font.bold: true
                font.pixelSize: 16
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
            background: Rectangle {
                radius: 9
                color: loginButton.down ? "#3d7fbf" : (loginButton.hovered ? "#5aa8e6" : "#4f9dde")
            }
            onClicked: doLogin()
        }

        ComboBox {
            id: sessionCombo
            width: parent.width
            height: 42
            model: sddm.SessionModel {}
            textRole: "name"
            visible: count > 1
            font.pixelSize: 14
            color: "#f5f6f8"
            background: Rectangle {
                radius: 9
                color: Qt.rgba(1, 1, 1, 0.06)
                border.color: Qt.rgba(1, 1, 1, 0.15)
                border.width: 1
            }
        }
    }

    // ---- botões de energia ----
    Row {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 34
        spacing: 28

        Text {
            text: "Reiniciar"
            color: "#9aa5b1"
            font.pixelSize: 15
            MouseArea {
                anchors.fill: parent
                onClicked: sddm.reboot()
            }
        }

        Text {
            text: "Desligar"
            color: "#9aa5b1"
            font.pixelSize: 15
            MouseArea {
                anchors.fill: parent
                onClicked: sddm.shutdown()
            }
        }
    }

    Connections {
        target: sddm
        onLoginFailed: {
            root.lastError = "Usuário ou senha inválidos"
            password.forceActiveFocus()
            password.selectAll()
        }
        onLoginSucceeded: {
            root.lastError = ""
        }
    }

    function doLogin() {
        root.lastError = ""
        var sessionIndex = sessionCombo.currentIndex >= 0 ? sessionCombo.currentIndex : 0
        sddm.login(username.text, password.text, sessionIndex)
    }

    Component.onCompleted: {
        if (username.text.length === 0) {
            username.forceActiveFocus()
        } else {
            password.forceActiveFocus()
        }
    }
}
