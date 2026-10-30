import QtQuick 2.0
import QtQuick.Controls 2.12
import SddmComponents 2.0

// =============================================================================
//  Pineapple OS — tema de login do SDDM
//
//  Continuidade visual com o boot: mesmo fundo lavanda escuro (#262426,
//  nível Kindle ~9%) e o abacaxi de contorno no topo. Relógio, avatar,
//  senha e botões de energia aparecem sobre esse fundo — sem wallpaper,
//  sem blur. Boot → login parecem a mesma tela.
// =============================================================================

Rectangle {
    id: root
    width: Screen.width
    height: Screen.height

    property string lastError: ""

    // fundo idêntico ao Plymouth/GRUB (#262426)
    color: "#262426"

    // ---- abacaxi de contorno (mesmo asset do boot) ----
    Image {
        id: logo
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        anchors.topMargin: Screen.height * 0.08
        source: "pineapple.png"
        width: Math.round(Screen.height * 0.14)
        height: width
        fillMode: Image.PreserveAspectFit
        opacity: 0.95
    }

    // ---- relógio e data ----
    Column {
        id: clockColumn
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: logo.bottom
        anchors.topMargin: Screen.height * 0.04
        spacing: 4

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            id: clockLabel
            text: clockTimer.text
            font.pixelSize: Math.round(Screen.height * 0.030)
            font.weight: Font.Light
            color: "#eceaed"
        }
    }

    Timer {
        id: clockTimer
        property string text: ""
        interval: 1000
        running: true
        repeat: true
        onTriggered: text = Qt.formatDateTime(new Date(), "HH:mm")
    }

    // ---- formulário de login ----
    Column {
        id: form
        anchors.centerIn: parent
        width: Math.max(Screen.width * 0.24, 300)
        spacing: 14

        Image {
            id: avatar
            anchors.horizontalCenter: parent.horizontalCenter
            source: "avatar.png"
            width: Math.round(Screen.height * 0.14)
            height: width
            fillMode: Image.PreserveAspectFit
        }

        Text {
            id: userLabel
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Usuário"
            font.pixelSize: Math.round(Screen.height * 0.020)
            font.weight: Font.Light
            color: "#eceaed"
        }

        TextField {
            id: username
            width: parent.width
            height: 44
            placeholderText: "Usuário"
            color: "#ffffff"
            placeholderTextColor: "#9a969a"
            font.pixelSize: 16
            horizontalAlignment: TextInput.AlignHCenter
            visible: root.defaultUser.length === 0
            background: Rectangle {
                radius: 12
                color: "#3c393c"
                border.color: username.activeFocus ? "#c2bec2" : "#4a474a"
                border.width: username.activeFocus ? 2 : 1
            }
            onAccepted: password.forceActiveFocus()
        }

        Text {
            id: errorText
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            text: root.lastError
            color: "#ff8a80"
            font.pixelSize: 14
            visible: root.lastError.length > 0
            wrapMode: Text.WordWrap
        }

        TextField {
            id: password
            width: parent.width
            height: 44
            placeholderText: "Senha"
            echoMode: TextInput.Password
            color: "#ffffff"
            placeholderTextColor: "#9a969a"
            font.pixelSize: 16
            horizontalAlignment: TextInput.AlignHCenter
            background: Rectangle {
                radius: 12
                color: "#3c393c"
                border.color: password.activeFocus ? "#c2bec2" : "#4a474a"
                border.width: password.activeFocus ? 2 : 1
            }
            onAccepted: doLogin()
            Keys.onEscapePressed: {
                password.text = ""
                root.lastError = ""
                password.forceActiveFocus()
            }
        }
    }

    // ---- botões de energia (rodapé) ----
    Row {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 44
        spacing: 40

        Text {
            text: "Reiniciar"
            color: "#eceaed"
            font.pixelSize: 15
            opacity: 0.85
            MouseArea {
                anchors.fill: parent
                onClicked: sddm.reboot()
            }
        }

        Text {
            text: "Desligar"
            color: "#eceaed"
            font.pixelSize: 15
            opacity: 0.85
            MouseArea {
                anchors.fill: parent
                onClicked: sddm.shutdown()
            }
        }
    }

    Connections {
        target: sddm
        onLoginFailed: {
            root.lastError = "Senha incorreta"
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
        var user = root.defaultUser.length > 0 ? root.defaultUser : username.text
        sddm.login(user, password.text, sessionIndex)
    }

    property string defaultUser: ""

    ComboBox {
        id: sessionCombo
        width: 1
        height: 1
        visible: false
        model: sddm.SessionModel {}
        textRole: "name"
    }

    Component.onCompleted: {
        if (sddm.user !== undefined && sddm.user.length > 0) {
            root.defaultUser = sddm.user
            userLabel.text = sddm.user
            password.forceActiveFocus()
        } else {
            userLabel.text = ""
            username.forceActiveFocus()
        }
    }
}
