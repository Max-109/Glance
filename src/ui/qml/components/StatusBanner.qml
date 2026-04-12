import QtQuick 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    property var theme
    property string kind: "neutral"
    property string message: ""
    property var iconLibrary

    radius: 8
    border.width: 1
    border.color: _borderColor()
    color: _backgroundColor()

    RowLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 10

        Image {
            source: root.iconLibrary ? root.iconLibrary.svgData(root._iconName(), root._iconColor()) : ""
            sourceSize.width: 16
            sourceSize.height: 16
            fillMode: Image.PreserveAspectFit
            Accessible.ignored: true
        }

        Text {
            text: root.message
            color: root._textColor()
            font.pixelSize: 13
            font.weight: 500
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }
    }

    function _iconName() {
        if (kind === "success") {
            return "check"
        }
        if (kind === "error") {
            return "triangle-alert"
        }
        return "circle-question-mark"
    }

    function _backgroundColor() {
        if (kind === "error") {
            return theme.surfaceCriticalWeak
        }
        if (kind === "success") {
            return theme.controlSurface
        }
        return theme.controlSurface
    }

    function _borderColor() {
        if (kind === "error") {
            return theme.borderCriticalSelected
        }
        if (kind === "success") {
            return theme.controlOutline
        }
        return theme.controlOutline
    }

    function _textColor() {
        if (kind === "error") {
            return theme.textOnCriticalBase
        }
        return theme.textStrong
    }

    function _iconColor() {
        if (kind === "error") {
            return theme.textOnCriticalBase
        }
        if (kind === "success") {
            return theme.iconStrongBase
        }
        return theme.iconBase
    }
}
