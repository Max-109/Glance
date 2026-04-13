import QtQuick 2.15
import QtQuick.Layouts 1.15
import QtQuick.Window 2.15

Rectangle {
    id: root

    property var theme
    property string kind: "neutral"
    property string message: ""
    property var iconLibrary
    readonly property real pixelRatio: Screen.devicePixelRatio > 0 ? Screen.devicePixelRatio : 1
    readonly property bool shown: message.length > 0
    property string displayKind: kind
    property string displayMessage: message

    radius: 8
    border.width: 1
    border.color: _borderColor()
    color: _backgroundColor()
    clip: true
    opacity: shown ? 1 : 0
    scale: shown ? 1 : 0.985
    implicitHeight: shown ? Math.max(42, contentRow.implicitHeight + 24) : 0
    visible: shown || opacity > 0.01

    transformOrigin: Item.Top

    Behavior on opacity {
        NumberAnimation { duration: 150; easing.type: Easing.OutCubic }
    }

    Behavior on scale {
        NumberAnimation { duration: 170; easing.type: Easing.OutCubic }
    }

    Behavior on implicitHeight {
        NumberAnimation { duration: 180; easing.type: Easing.OutCubic }
    }

    onMessageChanged: {
        if (message.length > 0) {
            displayMessage = message
        }
    }

    onKindChanged: {
        if (message.length > 0) {
            displayKind = kind
        }
    }

    RowLayout {
        id: contentRow
        anchors.fill: parent
        anchors.margins: 12
        spacing: 10

        Image {
            source: root.iconLibrary ? root.iconLibrary.svgData(root._iconName(), root._iconColor()) : ""
            sourceSize.width: Math.round(16 * root.pixelRatio)
            sourceSize.height: Math.round(16 * root.pixelRatio)
            fillMode: Image.PreserveAspectFit
            smooth: true
            Layout.preferredWidth: 16
            Layout.preferredHeight: 16
            Accessible.ignored: true
        }

        Text {
            text: root.displayMessage
            color: root._textColor()
            font.pixelSize: 13
            font.weight: 500
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }
    }

    function _iconName() {
        if (displayKind === "success") {
            return "check"
        }
        if (displayKind === "error") {
            return "triangle-alert"
        }
        return "circle-question-mark"
    }

    function _backgroundColor() {
        if (displayKind === "error") {
            return theme.surfaceCriticalWeak
        }
        if (displayKind === "success") {
            return theme.controlSurface
        }
        return theme.controlSurface
    }

    function _borderColor() {
        if (displayKind === "error") {
            return theme.borderCriticalSelected
        }
        if (displayKind === "success") {
            return theme.controlOutline
        }
        return theme.controlOutline
    }

    function _textColor() {
        if (displayKind === "error") {
            return theme.textOnCriticalBase
        }
        return theme.textStrong
    }

    function _iconColor() {
        if (displayKind === "error") {
            return theme.textOnCriticalBase
        }
        if (displayKind === "success") {
            return theme.iconStrongBase
        }
        return theme.iconBase
    }
}
