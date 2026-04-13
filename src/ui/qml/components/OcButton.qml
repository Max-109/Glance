import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Window 2.15

Button {
    id: root

    property var theme
    property string variant: "secondary"
    property string iconName: ""
    property var iconLibrary
    property string accessibleLabel: ""
    readonly property real pixelRatio: Screen.devicePixelRatio > 0 ? Screen.devicePixelRatio : 1
    readonly property bool iconOnly: root.text.length === 0
    readonly property bool activePress: root.down || root.checked
    readonly property int iconVisualWidth: root.iconName.length > 0 ? 16 : 0
    readonly property int contentGap: root.iconName.length > 0 && root.text.length > 0 ? 8 : 0

    implicitHeight: iconOnly ? 32 : 34
    implicitWidth: iconOnly
        ? 32
        : Math.max(96, labelMetrics.implicitWidth + leftPadding + rightPadding + iconVisualWidth + contentGap)

    padding: 0
    leftPadding: iconOnly ? 8 : 12
    rightPadding: iconOnly ? 8 : 12
    topPadding: 0
    bottomPadding: 0
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    Accessible.name: root.accessibleLabel.length > 0 ? root.accessibleLabel : (root.text.length > 0 ? root.text : root.iconName)

    contentItem: Item {
        x: root.leftPadding
        y: root.topPadding + (root.activePress ? 1 : 0)
        width: root.availableWidth
        height: root.availableHeight
        implicitWidth: Math.max(icon.implicitWidth, labelMetrics.implicitWidth)
        implicitHeight: Math.max(icon.implicitHeight, label.implicitHeight)

        Behavior on y {
            NumberAnimation { duration: 70; easing.type: Easing.OutCubic }
        }

        Image {
            id: icon
            visible: root.iconName.length > 0
            width: visible ? 16 : 0
            height: visible ? 16 : 0
            x: root.iconOnly
                ? Math.round((parent.width - width) / 2)
                : 0
            y: Math.round((parent.height - height) / 2)
            source: root.iconLibrary ? root.iconLibrary.svgData(root.iconName, root._foregroundColor()) : ""
            sourceSize.width: Math.round(16 * root.pixelRatio)
            sourceSize.height: Math.round(16 * root.pixelRatio)
            fillMode: Image.PreserveAspectFit
            smooth: true
            Accessible.ignored: true
        }

        Text {
            id: label
            visible: root.text.length > 0
            text: root.text
            color: root._foregroundColor()
            font.pixelSize: 13
            font.weight: 500
            renderType: Text.NativeRendering
            width: Math.min(labelMetrics.implicitWidth, parent.width - root.rightPadding - (root.iconOnly ? 0 : 0))
            height: implicitHeight
            x: Math.round((parent.width - width) / 2)
            y: Math.round((parent.height - height) / 2)
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }

        Text {
            id: labelMetrics
            visible: false
            text: root.text
            font.pixelSize: 13
            font.weight: 500
        }
    }

    background: Rectangle {
        radius: root.iconOnly ? 4 : 6
        color: root._backgroundColor()
        border.width: root._borderWidth()
        border.color: root._borderColor()

        Behavior on color {
            ColorAnimation { duration: 110; easing.type: Easing.OutCubic }
        }

        Behavior on border.color {
            ColorAnimation { duration: 110; easing.type: Easing.OutCubic }
        }
    }

    function _backgroundColor() {
        if (!enabled) {
            if (variant === "primary") {
                return theme.buttonSecondaryDisabled
            }
            if (variant === "secondary") {
                return theme.buttonSecondaryDisabled
            }
            if (variant === "danger") {
                return theme.surfaceCriticalWeak
            }
            return "transparent"
        }
        if (variant === "primary") {
            return activePress
                ? theme.buttonPrimaryActive
                : (hovered ? theme.buttonPrimaryHover : theme.buttonPrimaryBase)
        }
        if (variant === "danger") {
            return activePress
                ? theme.surfaceBaseActive
                : (hovered ? theme.surfaceBaseHover : theme.surfaceCriticalWeak)
        }
        if (variant === "ghost") {
            return activePress
                ? theme.surfaceBaseActive
                : (hovered ? theme.surfaceBaseHover : "transparent")
        }
        return activePress
            ? theme.surfaceRaisedBaseActive
            : (hovered ? theme.buttonSecondaryHover : theme.buttonSecondaryBase)
    }

    function _borderColor() {
        if (variant === "ghost") {
            if (activePress || visualFocus) {
                return theme.borderSelected
            }
            return hovered ? theme.borderHover : "transparent"
        }
        if (variant === "danger") {
            return theme.borderCriticalSelected
        }
        if (activePress || visualFocus) {
            return theme.borderSelected
        }
        return hovered ? theme.borderHover : theme.borderWeakBase
    }

    function _borderWidth() {
        if (variant === "ghost") {
            return hovered || activePress || visualFocus ? 1 : 0
        }
        return 1
    }

    function _foregroundColor() {
        if (!enabled) {
            if (variant === "primary") {
                return theme.iconStrongDisabled
            }
            if (variant === "ghost" && iconOnly) {
                return theme.iconDisabled
            }
            return theme.textWeak
        }
        if (variant === "primary") {
            return theme.iconInvertBase
        }
        if (variant === "danger") {
            return theme.textOnCriticalBase
        }
        if (variant === "ghost" && iconOnly) {
            return activePress
                ? theme.iconActive
                : (hovered ? theme.iconHover : theme.iconBase)
        }
        return theme.textStrong
    }
}
