import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Window 2.15

Button {
    id: root

    property var theme
    property string variant: "secondary"
    property string iconName: ""
    property var iconLibrary
    property string accessibleLabel: ""
    readonly property real pixelRatio: Screen.devicePixelRatio > 0 ? Screen.devicePixelRatio : 1

    implicitHeight: 34
    implicitWidth: root.text.length > 0
        ? Math.max(96, contentItem.implicitWidth + 24)
        : 32
    hoverEnabled: true
    Accessible.name: root.accessibleLabel.length > 0 ? root.accessibleLabel : (root.text.length > 0 ? root.text : root.iconName)

    contentItem: RowLayout {
        spacing: 8
        anchors.centerIn: parent

        Image {
            visible: root.iconName.length > 0
            source: root.iconLibrary ? root.iconLibrary.svgData(root.iconName, root._foregroundColor()) : ""
            sourceSize.width: Math.round(16 * root.pixelRatio)
            sourceSize.height: Math.round(16 * root.pixelRatio)
            fillMode: Image.PreserveAspectFit
            Layout.preferredWidth: visible ? 16 : 0
            Layout.preferredHeight: visible ? 16 : 0
            smooth: true
            Accessible.ignored: true
        }

        Text {
            visible: root.text.length > 0
            text: root.text
            color: root._foregroundColor()
            font.pixelSize: 13
            font.weight: 500
            renderType: Text.QtRendering
            elide: Text.ElideRight
        }
    }

    background: Rectangle {
        radius: 6
        border.width: root.variant === "ghost" ? (root.hovered ? 1 : 0) : 1
        border.color: root._borderColor()
        color: root._backgroundColor()

        Behavior on color { ColorAnimation { duration: 140 } }
        Behavior on border.color { ColorAnimation { duration: 140 } }
    }

    function _backgroundColor() {
        if (variant === "primary") {
            return down ? theme.surfaceRaisedBaseActive : (hovered ? theme.surfaceBaseHover : theme.buttonPrimaryBase)
        }
        if (variant === "danger") {
            return hovered ? theme.surfaceBaseHover : theme.surfaceCriticalWeak
        }
        if (variant === "ghost") {
            return down ? theme.surfaceBaseActive : (hovered ? theme.surfaceBaseHover : "transparent")
        }
        return hovered ? theme.buttonSecondaryHover : theme.buttonSecondaryBase
    }

    function _borderColor() {
        if (variant === "primary") {
            return theme.borderWeakBase
        }
        if (variant === "danger") {
            return theme.borderCriticalSelected
        }
        if (variant === "ghost") {
            return "transparent"
        }
        return theme.borderWeakBase
    }

    function _foregroundColor() {
        if (variant === "ghost" && root.text.length === 0) {
            return hovered ? theme.iconStrongBase : theme.iconHover
        }
        if (variant === "primary") {
            return theme.textStrong
        }
        if (variant === "danger") {
            return theme.textOnCriticalBase
        }
        return theme.textStrong
    }
}
