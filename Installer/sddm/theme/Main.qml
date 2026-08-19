import QtQuick 2.0
import QtQuick.Controls 2.12
import SddmComponents 2.0

// =============================================================================
//  Pineapple OS — tema de login do SDDM (estilo macOS)
//
//  Reproduz a tela de login do macOS:
//    * wallpaper desfocado/escurecido como fundo;
//    * relógio e data no centro superior;
//    * avatar do usuário centralizado (círculo) + campo de senha;
//    * botões de energia (Reiniciar / Desligar) no rodapé.
// =============================================================================

Rectangle {
    id: root
    width: Screen.width
    height: Screen.height

    property string lastError: ""

    color: "#1d2430"

    // ---- fundo: wallpaper do sistema (fallback para background.png) ----
    Image {
        id: bg
        anchors.fill: parent
        source: {
            // Tenta usar o wallpaper ativo (High Sierra / Catalina / Sequoia).
            var paths = [
                "/usr/share/backgrounds/pineappleos/highsierra.svg",
                "/usr/share/backgrounds/pineappleos/wallpaper.svg"
            ]
            var base = "file://" + paths[0]
            return base
        }
        fillMode: Image.PreserveAspectCrop
    }

    // Escurecimento estilo macOS (o login escurece o wallpaper)
    Rectangle {
        anchors.fill: parent
        color: "#0a0e14"
        opacity: 0.55
    }

    // ---- relógio e data (topo central) ----
    Column {
        id: clockColumn
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        anchors.topMargin: Screen.height * 0.10
        spacing: 4

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            id: clockLabel
            text: clockTimer.text
            font.pixelSize: Math.round(Screen.height * 0.034)
            font.weight: Font.Light
            color: "#f5f6f8"
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

    // ---- formulário de login (estilo macOS) ----
    Column {
        id: form
        anchors.centerIn: parent
        width: Math.max(Screen.width * 0.24, 300)
        spacing: 14

        // Avatar do usuário (círculo, gerado por gen-backgrounds.py)
        Image {
            id: avatar
            anchors.horizontalCenter: parent.horizontalCenter
            source: "avatar.png"
            width: Math.round(Screen.height * 0.16)
            height: width
            fillMode: Image.PreserveAspectFit
        }

        // Nome do usuário logado (como o macOS mostra o nome + avatar)
        Text {
            id: userLabel
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Usuário"
            font.pixelSize: Math.round(Screen.height * 0.022)
            font.weight: Font.Light
            color: "#f5f6f8"
        }

        // Campo de usuário — visível apenas quando o SDDM não informa o
        // usuário padrão (na prática o macOS já mostra o nome logado).
        TextField {
            id: username
            width: parent.width
            height: 44
            placeholderText: "Usuário"
            color: "#ffffff"
            placeholderTextColor: "#b7c0cc"
            font.pixelSize: 16
            horizontalAlignment: TextInput.AlignHCenter
            visible: root.defaultUser.length === 0
            background: Rectangle {
                radius: 12
                color: Qt.rgba(0.08, 0.09, 0.12, 0.55)
                border.color: username.activeFocus ? "#7fb7e8" : Qt.rgba(1, 1, 1, 0.22)
                border.width: username.activeFocus ? 2 : 1
            }
            onAccepted: password.forceActiveFocus()
        }

        // Mensagem de erro (usuário/senha inválidos)
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

        // Campo de senha (translúcido, arredondado, estilo macOS)
        TextField {
            id: password
            width: parent.width
            height: 44
            placeholderText: "Senha"
            echoMode: TextInput.Password
            color: "#ffffff"
            placeholderTextColor: "#b7c0cc"
            font.pixelSize: 16
            horizontalAlignment: TextInput.AlignHCenter
            background: Rectangle {
                radius: 12
                color: Qt.rgba(0.08, 0.09, 0.12, 0.55)
                border.color: password.activeFocus ? "#7fb7e8" : Qt.rgba(1, 1, 1, 0.22)
                border.width: password.activeFocus ? 2 : 1
            }
            onAccepted: doLogin()
            Keys.onEscapePressed: {
                password.text = ""
                root.lastError = ""
                password.forceActiveFocus()
            }
        }

        // Botão "Entrar" (acento azul, estilo macOS)
        Button {
            id: loginButton
            width: parent.width
            height: 44
            text: "Entrar"
            visible: false // no macOS clicar na senha é suficiente
            onClicked: doLogin()
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
            color: "#eef2f7"
            font.pixelSize: 15
            opacity: 0.85
            MouseArea {
                anchors.fill: parent
                onClicked: sddm.reboot()
            }
        }

        Text {
            text: "Desligar"
            color: "#eef2f7"
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

    // Nome de usuário preenchido automaticamente pelo SDDM (se disponível)
    property string defaultUser: ""

    // Seleção de sessão (quando há mais de uma)
    ComboBox {
        id: sessionCombo
        width: 1
        height: 1
        visible: false
        model: sddm.SessionModel {}
        textRole: "name"
    }

    Component.onCompleted: {
        // Preenche o nome do usuário com o usuário padrão do SDDM
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